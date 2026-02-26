/// Chat message model for the UI.
library;

class ChatMessage {
  final String id;
  final String text;
  final bool isAssistant;
  final String? imageUrl;
  final List<ChatCitation> citations;
  final DateTime timestamp;

  const ChatMessage({
    required this.id,
    required this.text,
    required this.isAssistant,
    this.imageUrl,
    this.citations = const [],
    required this.timestamp,
  });
}

class ChatCitation {
  final String memoryId;
  final String sourceUri;
  final String title;

  const ChatCitation({
    required this.memoryId,
    required this.sourceUri,
    required this.title,
  });

  factory ChatCitation.fromJson(Map<String, dynamic> json) {
    return ChatCitation(
      memoryId: (json['memory_id'] ?? '').toString(),
      sourceUri: (json['source_uri'] ?? '').toString(),
      title: (json['title'] ?? 'Untitled').toString(),
    );
  }
}
