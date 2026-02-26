/// Semantic search screen — dedicated RAG search with advanced filtering.
library;

import 'dart:async';

import 'package:flutter/material.dart';

import '../../models/memory.dart';
import '../../services/api_client.dart';
import '../../theme/app_theme.dart';
import '../../widgets/glass_card.dart';

class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key});

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final TextEditingController _searchController = TextEditingController();
  final ApiClient _api = ApiClient();
  final List<Memory> _results = [];
  bool _loading = false;
  bool _hasSearched = false;
  Timer? _debounce;

  // Filters
  String? _mediaFilter;
  String? _memoryTypeFilter;

  final _mediaTypes = ['All', 'text', 'image', 'video', 'audio', 'document'];

  @override
  void dispose() {
    _debounce?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  void _onSearchChanged(String query) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 500), () {
      if (query.trim().length >= 2) {
        _performSearch(query.trim());
      }
    });
  }

  Future<void> _performSearch(String query) async {
    setState(() => _loading = true);

    try {
      final results = await _api.searchMemories(query: query);
      if (!mounted) return;
      setState(() {
        _results
          ..clear()
          ..addAll(results);
        _loading = false;
        _hasSearched = true;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  List<Memory> get _filteredResults {
    var results = _results;
    if (_mediaFilter != null) {
      results = results.where((m) => m.mediaType == _mediaFilter).toList();
    }
    if (_memoryTypeFilter != null) {
      results =
          results.where((m) => m.memoryType == _memoryTypeFilter).toList();
    }
    return results;
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
    final filtered = _filteredResults;

    return SafeArea(
      child: Column(
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Search Memories',
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
                const SizedBox(height: 12),

                // Search bar
                Container(
                  decoration: BoxDecoration(
                    color: SynapseColors.surfaceLight,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(
                        color: SynapseColors.glassBorder, width: 0.5),
                  ),
                  child: TextField(
                    controller: _searchController,
                    onChanged: _onSearchChanged,
                    onSubmitted: (q) {
                      if (q.trim().isNotEmpty) _performSearch(q.trim());
                    },
                    style: const TextStyle(
                      fontSize: 15,
                      color: SynapseColors.textPrimary,
                    ),
                    decoration: InputDecoration(
                      hintText: 'Search across all memories...',
                      hintStyle:
                          const TextStyle(color: SynapseColors.textMuted),
                      prefixIcon: const Icon(Icons.search_rounded,
                          color: SynapseColors.textMuted),
                      suffixIcon: _searchController.text.isNotEmpty
                          ? IconButton(
                              icon: const Icon(Icons.clear_rounded,
                                  color: SynapseColors.textMuted, size: 20),
                              onPressed: () {
                                _searchController.clear();
                                setState(() {
                                  _results.clear();
                                  _hasSearched = false;
                                });
                              },
                            )
                          : null,
                      border: InputBorder.none,
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 14),
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Filter chips
          SizedBox(
            height: 42,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              children: [
                ..._mediaTypes.map((t) {
                  final isSelected =
                      (t == 'All' && _mediaFilter == null) || t == _mediaFilter;
                  return Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: FilterChip(
                      label: Text(
                        t.toUpperCase(),
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w600,
                          color: isSelected
                              ? Colors.white
                              : SynapseColors.textSecondary,
                        ),
                      ),
                      selected: isSelected,
                      onSelected: (_) {
                        setState(() => _mediaFilter = t == 'All' ? null : t);
                      },
                      backgroundColor: SynapseColors.surfaceCard,
                      selectedColor: SynapseColors.accent,
                      side: const BorderSide(color: SynapseColors.glassBorder),
                      padding: const EdgeInsets.symmetric(
                          horizontal: 6, vertical: 2),
                    ),
                  );
                }),
              ],
            ),
          ),

          const SizedBox(height: 8),

          // Results
          Expanded(
            child: _loading
                ? const Center(
                    child:
                        CircularProgressIndicator(color: SynapseColors.primary))
                : !_hasSearched
                    ? _EmptySearchState()
                    : filtered.isEmpty
                        ? _NoResultsState()
                        : ListView.builder(
                            padding: const EdgeInsets.only(bottom: 20),
                            itemCount: filtered.length,
                            itemBuilder: (_, i) => _SearchResultCard(
                              memory: filtered[i],
                              rank: i + 1,
                              color: _memoryColor(filtered[i].memoryType),
                              mediaIcon: _mediaIcon(filtered[i].mediaType),
                            ),
                          ),
          ),
        ],
      ),
    );
  }
}

// ── Empty states ────────────────────────────────────────────────────────

class _EmptySearchState extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: SynapseGradients.cardGlow,
              shape: BoxShape.circle,
            ),
            child: const Icon(
              Icons.search_rounded,
              size: 48,
              color: SynapseColors.accent,
            ),
          ),
          const SizedBox(height: 24),
          const Text(
            'Semantic Search',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w700,
              color: SynapseColors.textPrimary,
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Search across all your memories using\nnatural language queries',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 14,
              color: SynapseColors.textSecondary,
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }
}

class _NoResultsState extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.search_off_rounded,
              size: 48, color: SynapseColors.textMuted),
          SizedBox(height: 16),
          Text(
            'No matching memories',
            style: TextStyle(color: SynapseColors.textMuted, fontSize: 16),
          ),
        ],
      ),
    );
  }
}

// ── Search result card ─────────────────────────────────────────────────

class _SearchResultCard extends StatelessWidget {
  final Memory memory;
  final int rank;
  final Color color;
  final IconData mediaIcon;

  const _SearchResultCard({
    required this.memory,
    required this.rank,
    required this.color,
    required this.mediaIcon,
  });

  @override
  Widget build(BuildContext context) {
    final scorePercent = (memory.score * 100).toStringAsFixed(1);

    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              // Rank badge
              Container(
                width: 28,
                height: 28,
                decoration: BoxDecoration(
                  gradient: SynapseGradients.primaryButton,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Center(
                  child: Text(
                    '$rank',
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: Colors.white,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              // Media icon
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(mediaIcon, color: color, size: 16),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  memory.title,
                  style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: SynapseColors.textPrimary,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              // Score badge
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: SynapseColors.primary.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  '$scorePercent%',
                  style: const TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    color: SynapseColors.primary,
                  ),
                ),
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
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ],
          const SizedBox(height: 8),
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
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
              if (memory.tags.isNotEmpty) ...[
                const SizedBox(width: 8),
                ...memory.tags.take(3).map((tag) => Padding(
                      padding: const EdgeInsets.only(right: 4),
                      child: Text(
                        '#$tag',
                        style: const TextStyle(
                          fontSize: 11,
                          color: SynapseColors.accent,
                        ),
                      ),
                    )),
              ],
            ],
          ),
        ],
      ),
    );
  }
}
