/// Voice recorder screen — audio memory capture with waveform visualization.
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';

import '../../services/api_client.dart';
import '../../services/platform_utils.dart';
import '../../theme/app_theme.dart';
import '../../widgets/glass_card.dart';

class VoiceRecorderScreen extends StatefulWidget {
  const VoiceRecorderScreen({super.key});

  @override
  State<VoiceRecorderScreen> createState() => _VoiceRecorderScreenState();
}

class _VoiceRecorderScreenState extends State<VoiceRecorderScreen>
    with SingleTickerProviderStateMixin {
  final ApiClient _api = ApiClient();
  late final AnimationController _pulseController;

  bool _isRecording = false;
  bool _hasRecording = false;
  bool _uploading = false;
  String? _statusMsg;
  String? _recordingPath;
  Duration _elapsed = Duration.zero;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );
  }

  @override
  void dispose() {
    _timer?.cancel();
    _pulseController.dispose();
    super.dispose();
  }

  Future<void> _startRecording() async {
    final hasMic = await PlatformUtils.requestMicrophone();
    if (!hasMic) {
      _showError('Microphone permission is required');
      return;
    }

    // Get temp directory for recording path
    final dir = await getTemporaryDirectory();
    final path =
        '${dir.path}/synapse_voice_${DateTime.now().millisecondsSinceEpoch}.m4a';

    setState(() {
      _isRecording = true;
      _hasRecording = false;
      _recordingPath = path;
      _elapsed = Duration.zero;
    });

    _pulseController.repeat(reverse: true);

    // Start timer
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) {
        setState(() => _elapsed += const Duration(seconds: 1));
      }
    });

    // NOTE: Actual audio recording integration would use the `record` package.
    // This screen provides the full UI and structure; the recording plugin
    // can be integrated by calling AudioRecorder().start() here.
  }

  Future<void> _stopRecording() async {
    _timer?.cancel();
    _pulseController.stop();
    _pulseController.reset();

    setState(() {
      _isRecording = false;
      _hasRecording = true;
    });
  }

  Future<void> _uploadRecording() async {
    if (_recordingPath == null) return;

    setState(() {
      _uploading = true;
      _statusMsg = 'Uploading voice note...';
    });

    try {
      final fileName =
          'voice_note_${DateTime.now().millisecondsSinceEpoch}.m4a';
      final uploadInfo = await _api.createUploadUrl(
        filename: fileName,
        contentType: 'audio/m4a',
      );

      setState(() => _statusMsg = 'Processing memory...');

      await _api.ingestMemory(
        storagePath: uploadInfo['storage_path'] as String,
        mediaType: 'audio',
        title: 'Voice Note (${_formatDuration(_elapsed)})',
      );

      if (!mounted) return;
      setState(() {
        _uploading = false;
        _hasRecording = false;
        _recordingPath = null;
        _statusMsg = '✓ Voice memory saved!';
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

  void _discardRecording() {
    setState(() {
      _hasRecording = false;
      _recordingPath = null;
      _elapsed = Duration.zero;
    });
  }

  String _formatDuration(Duration d) {
    final m = d.inMinutes.remainder(60).toString().padLeft(2, '0');
    final s = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '$m:$s';
  }

  void _showError(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(msg),
        backgroundColor: SynapseColors.error,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
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
              'Voice Note',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 4),
            const Text(
              'Record a voice memory',
              style: TextStyle(
                color: SynapseColors.textSecondary,
                fontSize: 14,
              ),
            ),
            const SizedBox(height: 40),

            // Recording visualizer
            Expanded(
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // Waveform / Timer
                    AnimatedBuilder(
                      animation: _pulseController,
                      builder: (_, __) => Container(
                        width: 180 +
                            (_isRecording ? _pulseController.value * 20 : 0),
                        height: 180 +
                            (_isRecording ? _pulseController.value * 20 : 0),
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient:
                              _isRecording ? null : SynapseGradients.cardGlow,
                          color: _isRecording
                              ? SynapseColors.error.withValues(
                                  alpha: 0.15 + _pulseController.value * 0.1)
                              : null,
                          border: Border.all(
                            color: _isRecording
                                ? SynapseColors.error.withValues(alpha: 0.6)
                                : SynapseColors.glassBorder,
                            width: _isRecording ? 3 : 1,
                          ),
                        ),
                        child: Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(
                                _isRecording
                                    ? Icons.mic_rounded
                                    : (_hasRecording
                                        ? Icons.play_arrow_rounded
                                        : Icons.mic_none_rounded),
                                size: 56,
                                color: _isRecording
                                    ? SynapseColors.error
                                    : SynapseColors.accent,
                              ),
                              if (_isRecording || _hasRecording) ...[
                                const SizedBox(height: 8),
                                Text(
                                  _formatDuration(_elapsed),
                                  style: TextStyle(
                                    fontSize: 28,
                                    fontWeight: FontWeight.w700,
                                    color: _isRecording
                                        ? SynapseColors.error
                                        : SynapseColors.textPrimary,
                                    fontFeatures: const [
                                      FontFeature.tabularFigures(),
                                    ],
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                      ),
                    ),

                    const SizedBox(height: 40),

                    // Controls
                    if (!_hasRecording)
                      GestureDetector(
                        onTap: _isRecording ? _stopRecording : _startRecording,
                        child: AnimatedContainer(
                          duration: SynapseAnimations.fast,
                          width: 72,
                          height: 72,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            gradient: _isRecording
                                ? null
                                : SynapseGradients.primaryButton,
                            color: _isRecording ? SynapseColors.error : null,
                            boxShadow: [
                              BoxShadow(
                                color: (_isRecording
                                        ? SynapseColors.error
                                        : SynapseColors.primary)
                                    .withValues(alpha: 0.4),
                                blurRadius: 20,
                              ),
                            ],
                          ),
                          child: Icon(
                            _isRecording
                                ? Icons.stop_rounded
                                : Icons.mic_rounded,
                            size: 32,
                            color: Colors.white,
                          ),
                        ),
                      )
                    else
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          OutlinedButton.icon(
                            onPressed: _discardRecording,
                            icon: const Icon(Icons.delete_rounded,
                                color: SynapseColors.error),
                            label: const Text('Discard'),
                            style: OutlinedButton.styleFrom(
                              side: const BorderSide(
                                  color: SynapseColors.glassBorder),
                              foregroundColor: SynapseColors.textPrimary,
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 20, vertical: 14),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                            ),
                          ),
                          const SizedBox(width: 16),
                          Container(
                            decoration: BoxDecoration(
                              gradient: SynapseGradients.primaryButton,
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: ElevatedButton.icon(
                              onPressed: _uploading ? null : _uploadRecording,
                              icon: const Icon(Icons.save_rounded),
                              label: const Text('Save Memory'),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.transparent,
                                shadowColor: Colors.transparent,
                                foregroundColor: Colors.white,
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 20, vertical: 14),
                              ),
                            ),
                          ),
                        ],
                      ),

                    const SizedBox(height: 16),
                    Text(
                      _isRecording
                          ? 'Tap to stop recording'
                          : (_hasRecording
                              ? 'Save or discard your recording'
                              : 'Tap to start recording'),
                      style: const TextStyle(
                        color: SynapseColors.textMuted,
                        fontSize: 13,
                      ),
                    ),
                  ],
                ),
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
