import 'dart:convert';

import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:http/http.dart' as http;

class ChatCitation {
  final String memoryId;
  final String sourceUri;
  final String title;

  ChatCitation({
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

class ChatResult {
  final String answer;
  final List<ChatCitation> citations;

  ChatResult({required this.answer, required this.citations});
}

class BackendApiService {
  final String _baseUrl = dotenv.env['BACKEND_API_BASE_URL'] ?? 'http://localhost:8000';
  final String _token = dotenv.env['BACKEND_AUTH_TOKEN'] ?? '';

  Future<ChatResult> chatMemory({required String message, int topK = 8}) async {
    if (_token.isEmpty) {
      throw Exception('Missing BACKEND_AUTH_TOKEN in .env');
    }

    final uri = Uri.parse('$_baseUrl/v1/memories/chat');
    final response = await http.post(
      uri,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $_token',
      },
      body: jsonEncode({'message': message, 'top_k': topK}),
    );

    if (response.statusCode != 200) {
      throw Exception('Backend chat failed (${response.statusCode}): ${response.body}');
    }

    final body = jsonDecode(response.body) as Map<String, dynamic>;
    final citations = (body['citations'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(ChatCitation.fromJson)
        .toList();

    return ChatResult(
      answer: (body['answer'] ?? "I don't have enough info to answer.").toString(),
      citations: citations,
    );
  }
}
