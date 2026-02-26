/// SynapseMemo — Premium dark-mode theme and color system.
///
/// Curated palette with glassmorphism, smooth gradients, and
/// micro-animation constants.
library;

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

// ── Color Palette ──────────────────────────────────────────────────────

class SynapseColors {
  SynapseColors._();

  // Primary gradients
  static const primary = Color(0xFF6C63FF);
  static const primaryLight = Color(0xFF9D97FF);
  static const primaryDark = Color(0xFF4A42D4);

  // Accent
  static const accent = Color(0xFF00D9FF);
  static const accentGlow = Color(0x3300D9FF);

  // Surfaces
  static const surface = Color(0xFF1A1B2E);
  static const surfaceLight = Color(0xFF222340);
  static const surfaceCard = Color(0xFF252648);
  static const surfaceElevated = Color(0xFF2D2E52);

  // Background
  static const background = Color(0xFF0F1023);
  static const backgroundGradientStart = Color(0xFF0F1023);
  static const backgroundGradientEnd = Color(0xFF1A1B3A);

  // Text
  static const textPrimary = Color(0xFFF0F0FF);
  static const textSecondary = Color(0xFF9CA3C0);
  static const textMuted = Color(0xFF5E6380);

  // Status
  static const success = Color(0xFF4ADE80);
  static const warning = Color(0xFFFBBF24);
  static const error = Color(0xFFEF4444);

  // Chat
  static const userBubble = Color(0xFF6C63FF);
  static const assistantBubble = Color(0xFF252648);

  // Glassmorphism
  static const glassBackground = Color(0x1AFFFFFF);
  static const glassBorder = Color(0x33FFFFFF);

  // Memory type colors
  static const memoryLife = Color(0xFFFF6B9D);
  static const memoryEpisodic = Color(0xFF4ECDC4);
  static const memoryPreferences = Color(0xFFFFD93D);
  static const memoryHobbies = Color(0xFF95E1D3);
  static const memoryKnowledge = Color(0xFF6C63FF);
  static const memoryLongTerm = Color(0xFFC084FC);
}

// ── Gradients ──────────────────────────────────────────────────────────

class SynapseGradients {
  SynapseGradients._();

  static const background = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      SynapseColors.backgroundGradientStart,
      SynapseColors.backgroundGradientEnd,
    ],
  );

  static const primaryButton = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      SynapseColors.primary,
      SynapseColors.accent,
    ],
  );

  static const cardGlow = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0x1A6C63FF),
      Color(0x0A00D9FF),
    ],
  );
}

// ── Theme ──────────────────────────────────────────────────────────────

ThemeData synapseDarkTheme() {
  final textTheme = GoogleFonts.interTextTheme(ThemeData.dark().textTheme);

  return ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    scaffoldBackgroundColor: SynapseColors.background,
    textTheme: textTheme.copyWith(
      headlineLarge: textTheme.headlineLarge?.copyWith(
        color: SynapseColors.textPrimary,
        fontWeight: FontWeight.w700,
      ),
      headlineMedium: textTheme.headlineMedium?.copyWith(
        color: SynapseColors.textPrimary,
        fontWeight: FontWeight.w600,
      ),
      bodyLarge: textTheme.bodyLarge?.copyWith(
        color: SynapseColors.textPrimary,
      ),
      bodyMedium: textTheme.bodyMedium?.copyWith(
        color: SynapseColors.textSecondary,
      ),
      labelLarge: textTheme.labelLarge?.copyWith(
        color: SynapseColors.textPrimary,
        fontWeight: FontWeight.w600,
      ),
    ),
    colorScheme: const ColorScheme.dark(
      primary: SynapseColors.primary,
      secondary: SynapseColors.accent,
      surface: SynapseColors.surface,
      error: SynapseColors.error,
      onPrimary: Colors.white,
      onSecondary: Colors.white,
      onSurface: SynapseColors.textPrimary,
    ),
    appBarTheme: AppBarTheme(
      backgroundColor: SynapseColors.surface.withValues(alpha: 0.9),
      foregroundColor: SynapseColors.textPrimary,
      elevation: 0,
      centerTitle: true,
      titleTextStyle: GoogleFonts.inter(
        fontSize: 18,
        fontWeight: FontWeight.w600,
        color: SynapseColors.textPrimary,
      ),
    ),
    cardTheme: CardThemeData(
      color: SynapseColors.surfaceCard,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: SynapseColors.glassBorder, width: 0.5),
      ),
    ),
    bottomNavigationBarTheme: const BottomNavigationBarThemeData(
      backgroundColor: SynapseColors.surface,
      selectedItemColor: SynapseColors.primary,
      unselectedItemColor: SynapseColors.textMuted,
      type: BottomNavigationBarType.fixed,
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: SynapseColors.primary,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        textStyle: GoogleFonts.inter(
          fontSize: 15,
          fontWeight: FontWeight.w600,
        ),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: SynapseColors.surfaceLight,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: SynapseColors.glassBorder),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: SynapseColors.glassBorder),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: SynapseColors.primary, width: 1.5),
      ),
      hintStyle: const TextStyle(color: SynapseColors.textMuted),
    ),
    dividerColor: SynapseColors.glassBorder,
  );
}

// ── Animation Constants ────────────────────────────────────────────────

class SynapseAnimations {
  SynapseAnimations._();

  static const fast = Duration(milliseconds: 200);
  static const normal = Duration(milliseconds: 350);
  static const slow = Duration(milliseconds: 600);
  static const curve = Curves.easeOutCubic;
}
