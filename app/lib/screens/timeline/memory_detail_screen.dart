/// Memory detail screen — full view of a single memory with metadata.
library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:share_plus/share_plus.dart';

import '../../models/memory.dart';
import '../../services/api_client.dart';
import '../../theme/app_theme.dart';
import '../../widgets/glass_card.dart';

class MemoryDetailScreen extends StatelessWidget {
  final Memory memory;

  const MemoryDetailScreen({super.key, required this.memory});

  Color get _memoryColor {
    switch (memory.memoryType) {
      case 'life_memory':
        return SynapseColors.memoryLife;
      case 'episodic_memory':
        return SynapseColors.memoryEpisodic;
      case 'preferences':
        return SynapseColors.memoryPreferences;
      case 'hobbies':
        return SynapseColors.memoryHobbies;
      case 'long_term_memory':
        return SynapseColors.memoryLongTerm;
      default:
        return SynapseColors.memoryKnowledge;
    }
  }

  IconData get _mediaIcon {
    switch (memory.mediaType) {
      case 'image':
        return Icons.image_rounded;
      case 'video':
        return Icons.videocam_rounded;
      case 'audio':
        return Icons.audiotrack_rounded;
      case 'document':
        return Icons.description_rounded;
      default:
        return Icons.text_snippet_rounded;
    }
  }

  @override
  Widget build(BuildContext context) {
    final dateStr = memory.capturedAt != null
        ? DateFormat('EEEE, MMM d, yyyy • h:mm a').format(memory.capturedAt!)
        : 'Date unknown';

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: SynapseGradients.background),
        child: SafeArea(
          child: Column(
            children: [
              // Header
              Padding(
                padding: const EdgeInsets.fromLTRB(8, 8, 8, 0),
                child: Row(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.arrow_back_ios_rounded,
                          color: SynapseColors.textPrimary),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                    const Spacer(),
                    IconButton(
                      icon: const Icon(Icons.share_rounded,
                          color: SynapseColors.textSecondary),
                      onPressed: () {
                        Share.share(
                          '${memory.title}\n\n${memory.summary}',
                          subject: 'SynapseMemo: ${memory.title}',
                        );
                      },
                    ),
                    IconButton(
                      icon: const Icon(Icons.delete_outline_rounded,
                          color: SynapseColors.error),
                      onPressed: () => _confirmDelete(context),
                    ),
                  ],
                ),
              ),

              // Content
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Type + media badge
                      Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: _memoryColor.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(14),
                            ),
                            child:
                                Icon(_mediaIcon, color: _memoryColor, size: 28),
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 8, vertical: 3),
                                  decoration: BoxDecoration(
                                    color: _memoryColor.withValues(alpha: 0.12),
                                    borderRadius: BorderRadius.circular(6),
                                  ),
                                  child: Text(
                                    memory.memoryType
                                        .replaceAll('_', ' ')
                                        .toUpperCase(),
                                    style: TextStyle(
                                      fontSize: 10,
                                      fontWeight: FontWeight.w700,
                                      color: _memoryColor,
                                      letterSpacing: 0.5,
                                    ),
                                  ),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  dateStr,
                                  style: const TextStyle(
                                    fontSize: 12,
                                    color: SynapseColors.textMuted,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),

                      const SizedBox(height: 20),

                      // Title
                      Text(
                        memory.title,
                        style: const TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.w700,
                          color: SynapseColors.textPrimary,
                          height: 1.3,
                        ),
                      ),

                      const SizedBox(height: 16),

                      // Summary
                      if (memory.summary.isNotEmpty)
                        GlassCard(
                          margin: EdgeInsets.zero,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Row(
                                children: [
                                  Icon(Icons.auto_awesome_rounded,
                                      size: 16, color: SynapseColors.accent),
                                  SizedBox(width: 8),
                                  Text(
                                    'AI Summary',
                                    style: TextStyle(
                                      fontSize: 12,
                                      fontWeight: FontWeight.w600,
                                      color: SynapseColors.accent,
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 10),
                              SelectableText(
                                memory.summary,
                                style: const TextStyle(
                                  fontSize: 15,
                                  height: 1.6,
                                  color: SynapseColors.textPrimary,
                                ),
                              ),
                            ],
                          ),
                        ),

                      const SizedBox(height: 16),

                      // Metadata
                      GlassCard(
                        margin: EdgeInsets.zero,
                        child: Column(
                          children: [
                            _MetadataRow(
                              label: 'Media Type',
                              value: memory.mediaType,
                              icon: _mediaIcon,
                              color: _memoryColor,
                            ),
                            const Divider(
                                color: SynapseColors.glassBorder, height: 20),
                            _MetadataRow(
                              label: 'Memory Type',
                              value: memory.memoryType.replaceAll('_', ' '),
                              icon: Icons.psychology_rounded,
                              color: _memoryColor,
                            ),
                            if (memory.score > 0) ...[
                              const Divider(
                                  color: SynapseColors.glassBorder, height: 20),
                              _MetadataRow(
                                label: 'Relevance',
                                value:
                                    '${(memory.score * 100).toStringAsFixed(1)}%',
                                icon: Icons.analytics_rounded,
                                color: SynapseColors.primary,
                              ),
                            ],
                            const Divider(
                                color: SynapseColors.glassBorder, height: 20),
                            _MetadataRow(
                              label: 'Memory ID',
                              value: memory.memoryId.length > 12
                                  ? '${memory.memoryId.substring(0, 12)}...'
                                  : memory.memoryId,
                              icon: Icons.fingerprint_rounded,
                              color: SynapseColors.textMuted,
                            ),
                          ],
                        ),
                      ),

                      // Tags
                      if (memory.tags.isNotEmpty) ...[
                        const SizedBox(height: 16),
                        GlassCard(
                          margin: EdgeInsets.zero,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'Tags',
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                  color: SynapseColors.textMuted,
                                  letterSpacing: 0.5,
                                ),
                              ),
                              const SizedBox(height: 10),
                              Wrap(
                                spacing: 8,
                                runSpacing: 8,
                                children: memory.tags
                                    .map((tag) => Container(
                                          padding: const EdgeInsets.symmetric(
                                              horizontal: 10, vertical: 6),
                                          decoration: BoxDecoration(
                                            color: SynapseColors.accent
                                                .withValues(alpha: 0.1),
                                            borderRadius:
                                                BorderRadius.circular(8),
                                            border: Border.all(
                                              color: SynapseColors.accent
                                                  .withValues(alpha: 0.3),
                                            ),
                                          ),
                                          child: Text(
                                            '#$tag',
                                            style: const TextStyle(
                                              fontSize: 13,
                                              color: SynapseColors.accent,
                                              fontWeight: FontWeight.w500,
                                            ),
                                          ),
                                        ))
                                    .toList(),
                              ),
                            ],
                          ),
                        ),
                      ],

                      const SizedBox(height: 32),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _confirmDelete(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: SynapseColors.surfaceCard,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text(
          'Delete Memory?',
          style: TextStyle(color: SynapseColors.textPrimary),
        ),
        content: const Text(
          'This action cannot be undone.',
          style: TextStyle(color: SynapseColors.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () async {
              Navigator.pop(ctx);
              final api = ApiClient();
              await api.deleteMemory(memory.memoryId);
              if (context.mounted) Navigator.pop(context, true);
            },
            child: const Text(
              'Delete',
              style: TextStyle(color: SynapseColors.error),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Metadata row ────────────────────────────────────────────────────────

class _MetadataRow extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final Color color;

  const _MetadataRow({
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 16, color: color),
        const SizedBox(width: 10),
        Text(
          label,
          style: const TextStyle(
            fontSize: 13,
            color: SynapseColors.textMuted,
          ),
        ),
        const Spacer(),
        Text(
          value,
          style: const TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w500,
            color: SynapseColors.textPrimary,
          ),
        ),
      ],
    );
  }
}
