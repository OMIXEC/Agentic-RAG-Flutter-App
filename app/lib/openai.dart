import 'dart:convert';

import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:http/http.dart' as http;

class OpenAIService {
  final String _googleApiKey = dotenv.env['GOOGLE_API_KEY'] ?? '';
  final String _geminiModel = dotenv.env['GEMINI_MODEL'] ?? 'gemini-2.5-flash';
  final String _vertexProject = dotenv.env['GOOGLE_CLOUD_PROJECT'] ?? '';
  final String _vertexLocation =
      dotenv.env['GOOGLE_CLOUD_LOCATION'] ?? 'us-central1';
  final String _vertexModel =
      dotenv.env['GOOGLE_VERTEX_MODEL'] ?? 'multimodalembedding@001';
  final String _vertexToken = dotenv.env['GOOGLE_VERTEX_ACCESS_TOKEN'] ?? '';
  final int _embeddingDimension =
      int.tryParse(dotenv.env['GOOGLE_VERTEX_EMBEDDING_DIMENSION'] ?? '1408') ??
          1408;

  Future<String> generateLLMResponse(String query, String contextString) async {
    if (_googleApiKey.isEmpty) {
      return 'Missing GOOGLE_API_KEY in .env';
    }

    final prompt = '''
Context: $contextString
Question: $query
If this context can answer the question, provide a concise answer.
Else say exactly: I don't have enough info to answer.
''';

    final uri = Uri.parse(
      'https://generativelanguage.googleapis.com/v1beta/models/$_geminiModel:generateContent?key=$_googleApiKey',
    );

    final requestBody = {
      'contents': [
        {
          'parts': [
            {'text': prompt},
          ],
        },
      ],
      'generationConfig': {
        'temperature': 0.2,
        'maxOutputTokens': 512,
      },
    };

    try {
      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(requestBody),
      );

      if (response.statusCode != 200) {
        return 'Gemini error: ${response.body}';
      }

      final responseBody = jsonDecode(response.body) as Map<String, dynamic>;
      final candidates = responseBody['candidates'] as List<dynamic>?;
      if (candidates == null || candidates.isEmpty) {
        return "I don't have enough info to answer.";
      }

      final parts = (candidates.first['content']?['parts'] as List<dynamic>?) ??
          const [];
      final textPart = parts.firstWhere(
        (part) => part is Map<String, dynamic> && part['text'] != null,
        orElse: () => <String, dynamic>{'text': "I don't have enough info to answer."},
      ) as Map<String, dynamic>;

      return textPart['text'] as String;
    } catch (e) {
      return 'Error generating LLM response: $e';
    }
  }

  Future<List<double>> generateEmbeddings(String query) async {
    if (_vertexToken.isEmpty || _vertexProject.isEmpty) {
      return [];
    }

    final uri = Uri.parse(
      'https://$_vertexLocation-aiplatform.googleapis.com/v1/projects/$_vertexProject/locations/$_vertexLocation/publishers/google/models/$_vertexModel:predict',
    );

    final requestBody = {
      'instances': [
        {'text': query},
      ],
      'parameters': {
        'dimension': _embeddingDimension,
      },
    };

    try {
      final response = await http.post(
        uri,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $_vertexToken',
        },
        body: jsonEncode(requestBody),
      );

      if (response.statusCode != 200) {
        return [];
      }

      final responseBody = jsonDecode(response.body) as Map<String, dynamic>;
      final predictions = responseBody['predictions'] as List<dynamic>?;
      if (predictions == null || predictions.isEmpty) {
        return [];
      }

      return List<double>.from(predictions.first['textEmbedding'] as List<dynamic>);
    } catch (_) {
      return [];
    }
  }
}
