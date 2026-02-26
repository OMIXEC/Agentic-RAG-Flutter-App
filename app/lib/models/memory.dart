/// Data model for a memory item returned by the API.
library;

class Memory {
  final String memoryId;
  final double score;
  final String summary;
  final String mediaType;
  final String memoryType;
  final String sourceUri;
  final String title;
  final DateTime? capturedAt;
  final List<String> tags;

  const Memory({
    required this.memoryId,
    required this.score,
    required this.summary,
    required this.mediaType,
    required this.memoryType,
    required this.sourceUri,
    required this.title,
    this.capturedAt,
    this.tags = const [],
  });

  factory Memory.fromJson(Map<String, dynamic> json) {
    return Memory(
      memoryId: (json['memory_id'] ?? '').toString(),
      score: (json['score'] as num?)?.toDouble() ?? 0.0,
      summary: (json['summary'] ?? '').toString(),
      mediaType: (json['media_type'] ?? 'text').toString(),
      memoryType: (json['memory_type'] ?? 'general_knowledge').toString(),
      sourceUri: (json['source_uri'] ?? '').toString(),
      title: (json['title'] ?? 'Untitled').toString(),
      capturedAt: json['captured_at'] != null
          ? DateTime.tryParse(json['captured_at'].toString())
          : null,
      tags: (json['tags'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          const [],
    );
  }
}
