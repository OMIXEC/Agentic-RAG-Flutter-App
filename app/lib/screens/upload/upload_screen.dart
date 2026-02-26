/// Upload screen — multimodal memory capture.
library;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../../services/api_client.dart';
import '../../theme/app_theme.dart';
import '../../widgets/glass_card.dart';

class UploadScreen extends StatefulWidget {
  const UploadScreen({super.key});

  @override
  State<UploadScreen> createState() => _UploadScreenState();
}

class _UploadScreenState extends State<UploadScreen> {
  final ApiClient _api = ApiClient();
  bool _uploading = false;
  String? _statusMsg;

  final _uploadOptions = [
    _UploadOption(
      icon: Icons.image_rounded,
      label: 'Image',
      description: 'Photos & screenshots',
      color: SynapseColors.memoryLife,
      mediaType: 'image',
      extensions: ['png', 'jpg', 'jpeg', 'webp', 'bmp'],
    ),
    _UploadOption(
      icon: Icons.videocam_rounded,
      label: 'Video',
      description: 'Recordings & clips',
      color: SynapseColors.memoryEpisodic,
      mediaType: 'video',
      extensions: ['mp4', 'mov', 'mkv', 'webm', 'avi'],
    ),
    _UploadOption(
      icon: Icons.audiotrack_rounded,
      label: 'Audio',
      description: 'Voice notes & music',
      color: SynapseColors.accent,
      mediaType: 'audio',
      extensions: ['mp3', 'wav', 'm4a', 'aac', 'flac', 'ogg'],
    ),
    _UploadOption(
      icon: Icons.description_rounded,
      label: 'Document',
      description: 'PDFs, docs & notes',
      color: SynapseColors.memoryKnowledge,
      mediaType: 'document',
      extensions: ['pdf', 'docx', 'txt', 'md', 'csv', 'json'],
    ),
    _UploadOption(
      icon: Icons.text_snippet_rounded,
      label: 'Text Note',
      description: 'Quick thought or fact',
      color: SynapseColors.memoryPreferences,
      mediaType: 'text',
      extensions: [],
    ),
  ];

  Future<void> _pickAndUpload(_UploadOption option) async {
    if (option.mediaType == 'text') {
      _showTextInput();
      return;
    }

    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: option.extensions,
    );

    if (result == null || result.files.isEmpty) return;

    final file = result.files.first;
    setState(() {
      _uploading = true;
      _statusMsg = 'Uploading ${file.name}...';
    });

    try {
      final uploadInfo = await _api.createUploadUrl(
        filename: file.name,
        contentType: 'application/octet-stream',
      );

      setState(() => _statusMsg = 'Processing memory...');

      await _api.ingestMemory(
        storagePath: uploadInfo['storage_path'] as String,
        mediaType: option.mediaType,
        title: file.name,
      );

      if (!mounted) return;
      setState(() {
        _uploading = false;
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

  void _showTextInput() {
    final textController = TextEditingController();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: SynapseColors.surfaceCard,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: EdgeInsets.fromLTRB(
          20,
          20,
          20,
          MediaQuery.of(ctx).viewInsets.bottom + 20,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Quick Memory Note',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: SynapseColors.textPrimary,
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: textController,
              maxLines: 5,
              autofocus: true,
              style: const TextStyle(color: SynapseColors.textPrimary),
              decoration: const InputDecoration(
                hintText: 'Write something to remember...',
              ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () async {
                  final text = textController.text.trim();
                  if (text.isEmpty) return;
                  Navigator.pop(ctx);
                  setState(() {
                    _uploading = true;
                    _statusMsg = 'Saving note...';
                  });
                  try {
                    await _api.ingestMemory(
                      storagePath: 'inline://text',
                      mediaType: 'text',
                      title: text.length > 60
                          ? '${text.substring(0, 60)}...'
                          : text,
                      notes: text,
                    );
                    if (!mounted) return;
                    setState(() {
                      _uploading = false;
                      _statusMsg = '✓ Note saved!';
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
                },
                child: const Text('Save Memory'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Capture Memory',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 4),
            const Text(
              'Upload files or write a quick note',
              style: TextStyle(
                color: SynapseColors.textSecondary,
                fontSize: 14,
              ),
            ),
            const SizedBox(height: 24),

            // Upload options grid
            Expanded(
              child: GridView.builder(
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  childAspectRatio: 1.1,
                  mainAxisSpacing: 12,
                  crossAxisSpacing: 12,
                ),
                itemCount: _uploadOptions.length,
                itemBuilder: (_, i) {
                  final opt = _uploadOptions[i];
                  return GestureDetector(
                    onTap: _uploading ? null : () => _pickAndUpload(opt),
                    child: AnimatedContainer(
                      duration: SynapseAnimations.fast,
                      decoration: BoxDecoration(
                        color: SynapseColors.surfaceCard,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                          color: SynapseColors.glassBorder,
                          width: 0.5,
                        ),
                      ),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Container(
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: opt.color.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(14),
                            ),
                            child: Icon(opt.icon, color: opt.color, size: 28),
                          ),
                          const SizedBox(height: 12),
                          Text(
                            opt.label,
                            style: const TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w600,
                              color: SynapseColors.textPrimary,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            opt.description,
                            style: const TextStyle(
                              fontSize: 11,
                              color: SynapseColors.textMuted,
                            ),
                          ),
                        ],
                      ),
                    ),
                  );
                },
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

class _UploadOption {
  final IconData icon;
  final String label;
  final String description;
  final Color color;
  final String mediaType;
  final List<String> extensions;

  const _UploadOption({
    required this.icon,
    required this.label,
    required this.description,
    required this.color,
    required this.mediaType,
    required this.extensions,
  });
}
