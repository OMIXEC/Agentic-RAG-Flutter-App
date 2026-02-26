import 'dart:convert';

import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:http/http.dart' as http;

class PineconeService {
  final String apiKey = dotenv.env['PINECONE_API_KEY'] ?? '';
  final String pineconeIndexHost = dotenv.env['PINECONE_INDEX_HOST'] ?? '';

  Future<Map<String, dynamic>> queryIndex(
    String _indexName,
    List<double> queryEmbeddings, {
    int topK = 3,
    bool includeMetadata = true,
  }) async {
    if (pineconeIndexHost.isEmpty || apiKey.isEmpty) {
      return {
        'error': 'Missing PINECONE_INDEX_HOST or PINECONE_API_KEY in .env',
      };
    }

    final url = 'https://$pineconeIndexHost/query';

    final requestBody = {
      'vector': queryEmbeddings,
      'topK': topK,
      'includeMetadata': includeMetadata,
    };

    try {
      final response = await http.post(
        Uri.parse(url),
        headers: {
          'Content-Type': 'application/json',
          'Api-Key': apiKey,
        },
        body: jsonEncode(requestBody),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }

      return {
        'error': 'Error querying Pinecone: ${response.statusCode} ${response.body}',
      };
    } catch (e) {
      return {'error': e.toString()};
    }
  }
}
