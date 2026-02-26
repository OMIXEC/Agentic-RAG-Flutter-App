import 'dart:convert';

import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:http/http.dart' as http;

class OpenAIService {
  final String _llmProvider = (dotenv.env['LLM_PROVIDER'] ?? 'gemini').toLowerCase();
  final String _embeddingProvider =
      (dotenv.env['EMBEDDING_PROVIDER'] ?? 'auto').toLowerCase();

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

  final String _openAiKey = dotenv.env['OPENAI_API_KEY'] ?? '';
  final String _openAiEmbeddingModel =
      dotenv.env['OPENAI_TEXT_EMBEDDING_MODEL'] ??
      dotenv.env['OPENAI_EMBEDDING_MODEL'] ??
      'text-embedding-3-large';
  final String _openAiChatModel =
      dotenv.env['OPENAI_CHAT_MODEL'] ?? 'gpt-4.1-mini';

  Future<String> generateLLMResponse(
    String query,
    String contextString, {
    String? memoryContext,
    String? imageUrl,
  }) async {
    if (_llmProvider == 'openai') {
      return _generateOpenAIResponse(
        query,
        contextString,
        memoryContext: memoryContext,
        imageUrl: imageUrl,
      );
    }

    final geminiAttempt = await _generateGeminiResponse(
      query,
      contextString,
      memoryContext: memoryContext,
      imageUrl: imageUrl,
    );

    if (geminiAttempt.startsWith('Error') && _openAiKey.isNotEmpty) {
      return _generateOpenAIResponse(
        query,
        contextString,
        memoryContext: memoryContext,
        imageUrl: imageUrl,
      );
    }

    return geminiAttempt;
  }

  Future<List<double>> generateEmbeddings(String query) async {
    if (_embeddingProvider == 'openai') {
      return _generateOpenAIEmbeddings(query);
    }

    if (_embeddingProvider == 'vertex') {
      return _generateVertexEmbeddings(query);
    }

    final vertex = await _generateVertexEmbeddings(query);
    if (vertex.isNotEmpty) {
      return vertex;
    }
    return _generateOpenAIEmbeddings(query);
  }

  Future<List<double>> _generateVertexEmbeddings(String query) async {
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
      'parameters': {'dimension': _embeddingDimension},
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

  Future<List<double>> _generateOpenAIEmbeddings(String query) async {
    if (_openAiKey.isEmpty) {
      return [];
    }

    const url = 'https://api.openai.com/v1/embeddings';
    final requestBody = {
      'input': query,
      'model': _openAiEmbeddingModel,
      'encoding_format': 'float',
    };

    try {
      final response = await http.post(
        Uri.parse(url),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $_openAiKey',
        },
        body: jsonEncode(requestBody),
      );

      if (response.statusCode != 200) {
        return [];
      }

      final responseBody = jsonDecode(response.body) as Map<String, dynamic>;
      return List<double>.from(responseBody['data'][0]['embedding'] as List<dynamic>);
    } catch (_) {
      return [];
    }
  }

  Future<String> _generateGeminiResponse(
    String query,
    String contextString, {
    String? memoryContext,
    String? imageUrl,
  }) async {
    if (_googleApiKey.isEmpty) {
      return 'Error: Missing GOOGLE_API_KEY in .env';
    }

    final prompt = '''
Memory:
${memoryContext ?? 'No memory context'}

Retrieved Context:
$contextString

User Question:
$query

If context can answer, respond concisely.
If context is insufficient, say exactly: I don't have enough info to answer.
${(imageUrl ?? '').isNotEmpty ? 'Image URL reference: $imageUrl' : ''}
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
        'maxOutputTokens': 700,
      },
    };

    try {
      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(requestBody),
      );

      if (response.statusCode != 200) {
        return 'Error: Gemini request failed (${response.statusCode})';
      }

      final responseBody = jsonDecode(response.body) as Map<String, dynamic>;
      final candidates = responseBody['candidates'] as List<dynamic>?;
      if (candidates == null || candidates.isEmpty) {
        return "I don't have enough info to answer.";
      }

      final parts = (candidates.first['content']?['parts'] as List<dynamic>?) ??
          const [];
      for (final part in parts) {
        final text = (part as Map<String, dynamic>)['text'];
        if (text is String && text.isNotEmpty) {
          return text;
        }
      }

      return "I don't have enough info to answer.";
    } catch (e) {
      return 'Error generating LLM response: $e';
    }
  }

  Future<String> _generateOpenAIResponse(
    String query,
    String contextString, {
    String? memoryContext,
    String? imageUrl,
  }) async {
    if (_openAiKey.isEmpty) {
      return 'Error: Missing OPENAI_API_KEY in .env';
    }

    final prompt = '''
Memory:
${memoryContext ?? 'No memory context'}

Retrieved Context:
$contextString

Question:
$query

If context can answer, respond concisely.
If context is insufficient, say exactly: I don't have enough info to answer.
''';

    final content = <Map<String, dynamic>>[
      {'type': 'text', 'text': prompt},
    ];

    if ((imageUrl ?? '').isNotEmpty) {
      content.add(
        {
          'type': 'image_url',
          'image_url': {'url': imageUrl},
        },
      );
    }

    final requestBody = {
      'model': _openAiChatModel,
      'messages': [
        {'role': 'system', 'content': 'You are a concise retrieval assistant.'},
        {
          'role': 'user',
          'content': content,
        },
      ],
      'temperature': 0.2,
    };

    try {
      final response = await http.post(
        Uri.parse('https://api.openai.com/v1/chat/completions'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $_openAiKey',
        },
        body: jsonEncode(requestBody),
      );

      if (response.statusCode != 200) {
        return 'Error: OpenAI request failed (${response.statusCode})';
      }

      final responseBody = jsonDecode(response.body) as Map<String, dynamic>;
      return responseBody['choices'][0]['message']['content'] as String? ??
          "I don't have enough info to answer.";
    } catch (e) {
      return 'Error generating OpenAI response: $e';
    }
  }
}
