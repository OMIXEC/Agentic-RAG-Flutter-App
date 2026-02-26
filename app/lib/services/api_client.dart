/// Dio-based API client for SynapseMemo backend.
///
/// Handles authentication, retries, and error handling.
library;

import 'package:dio/dio.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../config/environment.dart';
import '../models/memory.dart';

class ApiClient {
  late final Dio _dio;

  ApiClient() {
    _dio = Dio(
      BaseOptions(
        baseUrl: Environment.apiBaseUrl,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 30),
        headers: {'Content-Type': 'application/json'},
      ),
    );

    // Auth interceptor — auto-attach Supabase token
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) {
        final session = Supabase.instance.client.auth.currentSession;
        if (session != null) {
          options.headers['Authorization'] = 'Bearer ${session.accessToken}';
        }
        handler.next(options);
      },
      onError: (error, handler) {
        // Auto-refresh on 401
        if (error.response?.statusCode == 401) {
          Supabase.instance.client.auth.refreshSession();
        }
        handler.next(error);
      },
    ));
  }

  // ── Upload URL ─────────────────────────────────────────────────────

  Future<Map<String, dynamic>> createUploadUrl({
    required String filename,
    required String contentType,
  }) async {
    final response = await _dio.post('/v1/memories/upload-url', data: {
      'filename': filename,
      'content_type': contentType,
    });
    return response.data as Map<String, dynamic>;
  }

  // ── Ingest ─────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> ingestMemory({
    required String storagePath,
    required String mediaType,
    String? title,
    String? notes,
    String? provider,
    List<String>? tags,
  }) async {
    final response = await _dio.post('/v1/memories/ingest', data: {
      'gcs_path': storagePath,
      'media_type': mediaType,
      if (title != null) 'title': title,
      if (notes != null) 'notes': notes,
      if (provider != null) 'provider': provider,
      if (tags != null) 'tags': tags,
    });
    return response.data as Map<String, dynamic>;
  }

  // ── Search ─────────────────────────────────────────────────────────

  Future<List<Memory>> searchMemories({
    required String query,
    int topK = 8,
    String? provider,
  }) async {
    final response = await _dio.post('/v1/memories/search', data: {
      'query': query,
      'top_k': topK,
      if (provider != null) 'provider': provider,
    });
    final results = (response.data['results'] as List<dynamic>?) ?? [];
    return results
        .map((r) => Memory.fromJson(r as Map<String, dynamic>))
        .toList();
  }

  // ── Chat ───────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> chatMemory({
    required String message,
    int topK = 8,
    String? provider,
  }) async {
    final response = await _dio.post('/v1/memories/chat', data: {
      'message': message,
      'top_k': topK,
      'stream': false,
      if (provider != null) 'provider': provider,
    });
    return response.data as Map<String, dynamic>;
  }

  // ── Timeline ───────────────────────────────────────────────────────

  Future<List<Memory>> getTimeline({
    int limit = 20,
    int offset = 0,
    String? memoryType,
  }) async {
    final queryParams = <String, dynamic>{
      'limit': limit,
      'offset': offset,
      if (memoryType != null) 'memory_type': memoryType,
    };
    final response = await _dio.get(
      '/v1/memories/timeline',
      queryParameters: queryParams,
    );
    final items = (response.data['items'] as List<dynamic>?) ?? [];
    return items
        .map((r) => Memory.fromJson(r as Map<String, dynamic>))
        .toList();
  }

  // ── Delete ─────────────────────────────────────────────────────────

  Future<bool> deleteMemory(String memoryId) async {
    final response = await _dio.delete('/v1/memories/$memoryId');
    return (response.data['deleted'] as bool?) ?? false;
  }

  // ── Promote ────────────────────────────────────────────────────────

  Future<int> promoteMemories() async {
    final response = await _dio.post('/v1/memories/promote');
    return (response.data['promoted_count'] as int?) ?? 0;
  }
}
