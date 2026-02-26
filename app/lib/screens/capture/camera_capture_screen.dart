/// Camera capture screen — native photo/video capture for memories.
///
/// Only used on mobile (iOS/Android). On web, falls back to image_picker.
library;

import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../services/api_client.dart';
import '../../services/platform_utils.dart';
import '../../theme/app_theme.dart';
import '../../widgets/glass_card.dart';

class CameraCaptureScreen extends StatefulWidget {
  const CameraCaptureScreen({super.key});

  @override
  State<CameraCaptureScreen> createState() => _CameraCaptureScreenState();
}

class _CameraCaptureScreenState extends State<CameraCaptureScreen>
    with SingleTickerProviderStateMixin {
  final ImagePicker _picker = ImagePicker();
  final ApiClient _api = ApiClient();
  XFile? _capturedFile;
  bool _isVideo = false;
  bool _uploading = false;
  String? _statusMsg;
  late final AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  Future<void> _capturePhoto() async {
    final hasPermission = await PlatformUtils.requestCamera();
    if (!hasPermission) {
      _showPermissionDenied('Camera');
      return;
    }

    final file = await _picker.pickImage(
      source: ImageSource.camera,
      maxWidth: 1920,
      maxHeight: 1080,
      imageQuality: 85,
    );

    if (file != null && mounted) {
      setState(() {
        _capturedFile = file;
        _isVideo = false;
      });
    }
  }

  Future<void> _captureVideo() async {
    final hasCam = await PlatformUtils.requestCamera();
    final hasMic = await PlatformUtils.requestMicrophone();
    if (!hasCam || !hasMic) {
      _showPermissionDenied('Camera & Microphone');
      return;
    }

    final file = await _picker.pickVideo(
      source: ImageSource.camera,
      maxDuration: const Duration(minutes: 5),
    );

    if (file != null && mounted) {
      setState(() {
        _capturedFile = file;
        _isVideo = true;
      });
    }
  }

  Future<void> _pickFromGallery() async {
    final hasPermission = await PlatformUtils.requestPhotos();
    if (!hasPermission) {
      _showPermissionDenied('Photos');
      return;
    }

    final file = await _picker.pickImage(source: ImageSource.gallery);
    if (file != null && mounted) {
      setState(() {
        _capturedFile = file;
        _isVideo = false;
      });
    }
  }

  Future<void> _uploadCapture() async {
    if (_capturedFile == null) return;

    setState(() {
      _uploading = true;
      _statusMsg = 'Uploading ${_isVideo ? "video" : "photo"}...';
    });

    try {
      final fileName = _capturedFile!.name;
      final uploadInfo = await _api.createUploadUrl(
        filename: fileName,
        contentType: _isVideo ? 'video/mp4' : 'image/jpeg',
      );

      setState(() => _statusMsg = 'Processing memory...');

      await _api.ingestMemory(
        storagePath: uploadInfo['storage_path'] as String,
        mediaType: _isVideo ? 'video' : 'image',
        title: fileName,
      );

      if (!mounted) return;
      setState(() {
        _uploading = false;
        _capturedFile = null;
        _statusMsg = '✓ Memory saved successfully!';
      });

      Future.delayed(const Duration(seconds: 2), () {
        if (mounted) setState(() => _statusMsg = null);
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _uploading = false;
        _statusMsg = 'Error: $e';
      });
    }
  }

  void _showPermissionDenied(String permission) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('$permission permission is required'),
        backgroundColor: SynapseColors.error,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    );
  }

  void _clearCapture() {
    setState(() {
      _capturedFile = null;
      _isVideo = false;
      _statusMsg = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Text(
              'Capture Memory',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 4),
            const Text(
              'Take a photo or record a video',
              style: TextStyle(
                color: SynapseColors.textSecondary,
                fontSize: 14,
              ),
            ),
            const SizedBox(height: 24),

            // Preview or capture buttons
            Expanded(
              child: _capturedFile != null
                  ? _PreviewCard(
                      file: _capturedFile!,
                      isVideo: _isVideo,
                      onRetake: _clearCapture,
                      onSave: _uploading ? null : _uploadCapture,
                    )
                  : _CaptureOptions(
                      onPhoto: _capturePhoto,
                      onVideo: _captureVideo,
                      onGallery: _pickFromGallery,
                      pulseController: _pulseController,
                    ),
            ),

            // Status
            if (_statusMsg != null || _uploading)
              GlassCard(
                margin: EdgeInsets.zero,
                child: Row(
                  children: [
                    if (_uploading)
                      const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: SynapseColors.primary,
                        ),
                      )
                    else
                      const Icon(Icons.check_circle_rounded,
                          color: SynapseColors.success, size: 20),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        _statusMsg ?? '',
                        style: const TextStyle(
                          fontSize: 14,
                          color: SynapseColors.textPrimary,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}

// ── Capture options ─────────────────────────────────────────────────────

class _CaptureOptions extends StatelessWidget {
  final VoidCallback onPhoto;
  final VoidCallback onVideo;
  final VoidCallback onGallery;
  final AnimationController pulseController;

  const _CaptureOptions({
    required this.onPhoto,
    required this.onVideo,
    required this.onGallery,
    required this.pulseController,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        // Main camera button
        AnimatedBuilder(
          animation: pulseController,
          builder: (_, __) => GestureDetector(
            onTap: onPhoto,
            child: Container(
              width: 100 + pulseController.value * 8,
              height: 100 + pulseController.value * 8,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: SynapseGradients.primaryButton,
                boxShadow: [
                  BoxShadow(
                    color: SynapseColors.primary
                        .withValues(alpha: 0.3 + pulseController.value * 0.2),
                    blurRadius: 20 + pulseController.value * 10,
                    spreadRadius: pulseController.value * 4,
                  ),
                ],
              ),
              child: const Icon(
                Icons.camera_alt_rounded,
                size: 44,
                color: Colors.white,
              ),
            ),
          ),
        ),
        const SizedBox(height: 16),
        const Text(
          'Tap to take photo',
          style: TextStyle(
            color: SynapseColors.textSecondary,
            fontSize: 14,
          ),
        ),
        const SizedBox(height: 40),

        // Secondary options
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: [
            _CaptureButton(
              icon: Icons.videocam_rounded,
              label: 'Video',
              color: SynapseColors.memoryEpisodic,
              onTap: onVideo,
            ),
            _CaptureButton(
              icon: Icons.photo_library_rounded,
              label: 'Gallery',
              color: SynapseColors.memoryKnowledge,
              onTap: onGallery,
            ),
          ],
        ),
      ],
    );
  }
}

class _CaptureButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  const _CaptureButton({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: color.withValues(alpha: 0.3)),
            ),
            child: Icon(icon, color: color, size: 28),
          ),
          const SizedBox(height: 8),
          Text(
            label,
            style: TextStyle(
              fontSize: 13,
              color: SynapseColors.textSecondary,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

// ── Preview card ────────────────────────────────────────────────────────

class _PreviewCard extends StatelessWidget {
  final XFile file;
  final bool isVideo;
  final VoidCallback onRetake;
  final VoidCallback? onSave;

  const _PreviewCard({
    required this.file,
    required this.isVideo,
    required this.onRetake,
    required this.onSave,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Expanded(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(20),
            child: Stack(
              fit: StackFit.expand,
              children: [
                if (!isVideo)
                  Image.file(
                    File(file.path),
                    fit: BoxFit.cover,
                  )
                else
                  Container(
                    decoration: BoxDecoration(
                      color: SynapseColors.surfaceCard,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: const Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.videocam_rounded,
                              size: 64, color: SynapseColors.memoryEpisodic),
                          SizedBox(height: 12),
                          Text(
                            'Video captured',
                            style: TextStyle(
                              color: SynapseColors.textPrimary,
                              fontSize: 16,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                // Overlay label
                Positioned(
                  top: 12,
                  left: 12,
                  child: Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: Colors.black54,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          isVideo ? Icons.videocam : Icons.photo,
                          size: 16,
                          color: Colors.white,
                        ),
                        const SizedBox(width: 6),
                        Text(
                          isVideo ? 'Video' : 'Photo',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: onRetake,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Retake'),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: SynapseColors.glassBorder),
                  foregroundColor: SynapseColors.textPrimary,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Container(
                decoration: BoxDecoration(
                  gradient: SynapseGradients.primaryButton,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: ElevatedButton.icon(
                  onPressed: onSave,
                  icon: const Icon(Icons.save_rounded),
                  label: const Text('Save Memory'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.transparent,
                    shadowColor: Colors.transparent,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }
}
