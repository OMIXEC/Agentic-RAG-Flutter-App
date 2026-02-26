/// Memory timeline — chronological view of all memories.
library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../models/memory.dart';
import '../../services/api_client.dart';
import '../../theme/app_theme.dart';
import '../../widgets/glass_card.dart';

class TimelineScreen extends StatefulWidget {
  const TimelineScreen({super.key});

  @override
  State<TimelineScreen> createState() => _TimelineScreenState();
}

class _TimelineScreenState extends State<TimelineScreen> {
  final ApiClient _api = ApiClient();
  final List<Memory> _memories = [];
  bool _loading = true;
  String? _filterType;

  final _memoryTypeFilters = [
    'All',
    'life_memory',
    'episodic_memory',
    'long_term_memory',
    'preferences',
    'hobbies',
    'general_knowledge',
  ];

  @override
  void initState() {
    super.initState();
    _loadTimeline();
  }

  Future<void> _loadTimeline() async {
    setState(() => _loading = true);
    try {
      final items = await _api.getTimeline(
        limit: 50,
        memoryType: _filterType,
      );
      if (!mounted) return;
      setState(() {
        _memories
          ..clear()
          ..addAll(items);
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  Color _memoryColor(String type) {
    switch (type) {
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

  IconData _mediaIcon(String type) {
    switch (type) {
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
    return SafeArea(
      child: Column(
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Your Memories',
                      style: Theme.of(context).textTheme.headlineMedium,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${_memories.length} memories stored',
                      style: TextStyle(
                        color: SynapseColors.textSecondary,
                        fontSize: 14,
                      ),
                    ),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: SynapseColors.primary.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(
                    Icons.psychology_rounded,
                    color: SynapseColors.primary,
                    size: 24,
                  ),
                ),
              ],
            ),
          ),

          // Filter chips
          SizedBox(
            height: 42,
            child: ListView.builder(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              itemCount: _memoryTypeFilters.length,
              itemBuilder: (_, i) {
                final filter = _memoryTypeFilters[i];
                final isSelected = (filter == 'All' && _filterType == null) ||
                    filter == _filterType;
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: FilterChip(
                    label: Text(
                      filter.replaceAll('_', ' ').toUpperCase(),
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: isSelected
                            ? Colors.white
                            : SynapseColors.textSecondary,
                      ),
                    ),
                    selected: isSelected,
                    onSelected: (_) {
                      setState(() {
                        _filterType = filter == 'All' ? null : filter;
                      });
                      _loadTimeline();
                    },
                    backgroundColor: SynapseColors.surfaceCard,
                    selectedColor: SynapseColors.primary,
                    side: const BorderSide(color: SynapseColors.glassBorder),
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  ),
                );
              },
            ),
          ),

          const SizedBox(height: 8),

          // Memory list
          Expanded(
            child: _loading
                ? const Center(
                    child: CircularProgressIndicator(
                      color: SynapseColors.primary,
                    ),
                  )
                : _memories.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              Icons.memory_rounded,
                              size: 64,
                              color:
                                  SynapseColors.textMuted.withValues(alpha: 0.3),
                            ),
                            const SizedBox(height: 16),
                            Text(
                              'No memories yet',
                              style: TextStyle(
                                color: SynapseColors.textMuted,
                                fontSize: 16,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Upload your first memory to get started',
                              style: TextStyle(
                                color: SynapseColors.textMuted
                                    .withValues(alpha: 0.6),
                                fontSize: 13,
                              ),
                            ),
                          ],
                        ),
                      )
                    : RefreshIndicator(
                        onRefresh: _loadTimeline,
                        color: SynapseColors.primary,
                        child: ListView.builder(
                          padding: const EdgeInsets.only(bottom: 20),
                          itemCount: _memories.length,
                          itemBuilder: (_, i) => _MemoryCard(
                            memory: _memories[i],
                            color: _memoryColor(_memories[i].memoryType),
                            mediaIcon: _mediaIcon(_memories[i].mediaType),
                            onDelete: () async {
                              await _api.deleteMemory(_memories[i].memoryId);
                              _loadTimeline();
                            },
                          ),
                        ),
                      ),
          ),
        ],
      ),
    );
  }
}

class _MemoryCard extends StatelessWidget {
  final Memory memory;
  final Color color;
  final IconData mediaIcon;
  final VoidCallback onDelete;

  const _MemoryCard({
    required this.memory,
    required this.color,
    required this.mediaIcon,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final dateStr = memory.capturedAt != null
        ? DateFormat('MMM d, yyyy').format(memory.capturedAt!)
        : '';

    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(mediaIcon, color: color, size: 20),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      memory.title,
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                        color: SynapseColors.textPrimary,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 2),
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 6,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: color.withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            memory.memoryType.replaceAll('_', ' '),
                            style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                              color: color,
                            ),
                          ),
                        ),
                        if (dateStr.isNotEmpty) ...[
                          const SizedBox(width: 8),
                          Text(
                            dateStr,
                            style: const TextStyle(
                              fontSize: 11,
                              color: SynapseColors.textMuted,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ],
                ),
              ),
              IconButton(
                icon: const Icon(Icons.more_vert_rounded, size: 20),
                color: SynapseColors.textMuted,
                onPressed: () {
                  showModalBottomSheet(
                    context: context,
                    backgroundColor: SynapseColors.surfaceCard,
                    shape: const RoundedRectangleBorder(
                      borderRadius:
                          BorderRadius.vertical(top: Radius.circular(16)),
                    ),
                    builder: (_) => SafeArea(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          ListTile(
                            leading: const Icon(Icons.delete_rounded,
                                color: SynapseColors.error),
                            title: const Text('Delete memory'),
                            onTap: () {
                              Navigator.pop(context);
                              onDelete();
                            },
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ],
          ),
          if (memory.summary.isNotEmpty) ...[
            const SizedBox(height: 10),
            Text(
              memory.summary,
              style: const TextStyle(
                fontSize: 13,
                height: 1.5,
                color: SynapseColors.textSecondary,
              ),
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
            ),
          ],
          if (memory.tags.isNotEmpty) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 6,
              children: memory.tags
                  .map((tag) => Chip(
                        label: Text(
                          '#$tag',
                          style: const TextStyle(
                            fontSize: 11,
                            color: SynapseColors.accent,
                          ),
                        ),
                        backgroundColor: SynapseColors.accent.withValues(alpha: 0.1),
                        side: BorderSide.none,
                        materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        padding: EdgeInsets.zero,
                        labelPadding:
                            const EdgeInsets.symmetric(horizontal: 6),
                      ))
                  .toList(),
            ),
          ],
        ],
      ),
    );
  }
}
