/// Environment configuration for the SynapseMemo app.
library;

import 'package:flutter_dotenv/flutter_dotenv.dart';

class Environment {
  Environment._();

  static String get apiBaseUrl =>
      dotenv.env['BACKEND_API_BASE_URL'] ?? 'http://localhost:8000';

  static String get supabaseUrl =>
      dotenv.env['SUPABASE_URL'] ?? '';

  static String get supabaseAnonKey =>
      dotenv.env['SUPABASE_ANON_KEY'] ?? '';
}
