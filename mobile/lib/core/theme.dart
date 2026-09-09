import 'package:flutter/material.dart';

abstract final class DilSeColours {
  static const mulberry = Color(0xFF5B2038);
  static const raspberry = Color(0xFFA94168);
  static const petal = Color(0xFFF6E5EA);
  static const paper = Color(0xFFFFF9F5);
  static const ink = Color(0xFF33242B);
  static const muted = Color(0xFF79666E);
  static const saffron = Color(0xFFE5A05B);
  static const leaf = Color(0xFF21675D);
  static const line = Color(0xFFE7D4DA);
}

ThemeData buildDilSeTheme() {
  final scheme = ColorScheme.fromSeed(
    seedColor: DilSeColours.mulberry,
    brightness: Brightness.light,
    primary: DilSeColours.mulberry,
    secondary: DilSeColours.raspberry,
    surface: DilSeColours.paper,
    onSurface: DilSeColours.ink,
    outline: DilSeColours.line,
  );
  final base = ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: DilSeColours.paper,
  );
  return base.copyWith(
    textTheme: base.textTheme.copyWith(
      displayLarge: const TextStyle(
        fontFamily: 'serif',
        fontSize: 42,
        height: 1.02,
        fontWeight: FontWeight.w600,
        letterSpacing: -1.4,
        color: DilSeColours.mulberry,
      ),
      headlineLarge: const TextStyle(
        fontFamily: 'serif',
        fontSize: 32,
        height: 1.08,
        fontWeight: FontWeight.w600,
        letterSpacing: -.8,
        color: DilSeColours.mulberry,
      ),
      headlineMedium: const TextStyle(
        fontFamily: 'serif',
        fontSize: 26,
        height: 1.12,
        fontWeight: FontWeight.w600,
        color: DilSeColours.mulberry,
      ),
      titleLarge: const TextStyle(
        fontSize: 19,
        height: 1.25,
        fontWeight: FontWeight.w700,
        color: DilSeColours.ink,
      ),
      bodyLarge: const TextStyle(
        fontSize: 16.5,
        height: 1.5,
        color: DilSeColours.ink,
      ),
      bodyMedium: const TextStyle(
        fontSize: 14.5,
        height: 1.48,
        color: DilSeColours.ink,
      ),
      labelLarge: const TextStyle(
        fontSize: 14,
        fontWeight: FontWeight.w700,
        letterSpacing: .1,
      ),
    ),
    appBarTheme: const AppBarTheme(
      elevation: 0,
      scrolledUnderElevation: 0,
      backgroundColor: DilSeColours.paper,
      foregroundColor: DilSeColours.ink,
      centerTitle: false,
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white.withValues(alpha: .84),
      contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(18),
        borderSide: const BorderSide(color: DilSeColours.line),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(18),
        borderSide: const BorderSide(color: DilSeColours.line),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(18),
        borderSide: const BorderSide(color: DilSeColours.raspberry, width: 1.5),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: DilSeColours.mulberry,
        foregroundColor: Colors.white,
        minimumSize: const Size.fromHeight(54),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: DilSeColours.mulberry,
        minimumSize: const Size.fromHeight(52),
        side: const BorderSide(color: DilSeColours.line),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      ),
    ),
    cardTheme: CardThemeData(
      color: Colors.white.withValues(alpha: .88),
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(24),
        side: const BorderSide(color: DilSeColours.line),
      ),
    ),
    bottomSheetTheme: const BottomSheetThemeData(
      backgroundColor: DilSeColours.paper,
      showDragHandle: true,
    ),
    dividerTheme: const DividerThemeData(
      color: DilSeColours.line,
      thickness: 1,
    ),
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      backgroundColor: DilSeColours.ink,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
    ),
  );
}
