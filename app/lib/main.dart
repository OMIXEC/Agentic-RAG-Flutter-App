import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'config/environment.dart';
import 'theme/app_theme.dart';
import 'screens/auth/login_screen.dart';
import 'screens/home/home_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load(fileName: '.env');

  // Initialize Supabase (safe to skip if not configured)
  final supabaseUrl = Environment.supabaseUrl;
  final supabaseKey = Environment.supabaseAnonKey;
  if (supabaseUrl.isNotEmpty && supabaseKey.isNotEmpty) {
    await Supabase.initialize(
      url: supabaseUrl,
      anonKey: supabaseKey,
    );
  }

  runApp(const SynapseMemoApp());
}

class SynapseMemoApp extends StatelessWidget {
  const SynapseMemoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SynapseMemo',
      debugShowCheckedModeBanner: false,
      theme: synapseDarkTheme(),
      home: const _AuthGate(),
    );
  }
}

/// Routes to login or home based on Supabase auth state.
class _AuthGate extends StatelessWidget {
  const _AuthGate();

  @override
  Widget build(BuildContext context) {
    // If Supabase isn't configured, go straight to home (dev mode)
    final supabaseUrl = Environment.supabaseUrl;
    if (supabaseUrl.isEmpty) {
      return const HomeScreen();
    }

    return StreamBuilder<AuthState>(
      stream: Supabase.instance.client.auth.onAuthStateChange,
      builder: (context, snapshot) {
        final session = snapshot.data?.session ??
            Supabase.instance.client.auth.currentSession;

        if (session != null) {
          return const HomeScreen();
        }

        return const LoginScreen();
      },
    );
  }
}
