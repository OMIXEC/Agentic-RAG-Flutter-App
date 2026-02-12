import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_dotenv/flutter_dotenv.dart';

class PineconeService {
  final String apiKey = dotenv.env['PINECONE_API_KEY'] ?? "";
  final String pineconeBaseUrl = dotenv.env['PINECONE_BASE_URL'] ?? "";

  Future<Map<String, dynamic>> queryIndex(
      String indexName, List<double> queryEmbeddings,
      {int topK = 2, bool includeMetadata = true}) async {
    final String url = "$pineconeBaseUrl/query";

    var requestBody = {
      "vector": queryEmbeddings,
      "topK": topK,
      "includeMetadata": includeMetadata,
    };

    try {
      final response = await http.post(
        Uri.parse(url),
        headers: {"Content-Type": "application/json", "Api-Key": apiKey},
        body: jsonEncode(requestBody),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception("Error querying Pinecone: ${response.body}");
      }
    } catch (e) {
      return {"error": e.toString()};
    }
  }
}
