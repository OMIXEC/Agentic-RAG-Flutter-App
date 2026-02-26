/// Platform detection utilities for conditional mobile/web behavior.
library;

import 'package:flutter/foundation.dart' show kIsWeb;
import 'dart:io' show Platform;

import 'package:permission_handler/permission_handler.dart';

class PlatformUtils {
  PlatformUtils._();

  /// True when running in a web browser.
  static bool get isWeb => kIsWeb;

  /// True on iOS (native, not Safari).
  static bool get isIOS => !kIsWeb && Platform.isIOS;

  /// True on Android (native, not Chrome).
  static bool get isAndroid => !kIsWeb && Platform.isAndroid;

  /// True on any native mobile platform.
  static bool get isMobile => isIOS || isAndroid;

  /// True on desktop (macOS, Windows, Linux).
  static bool get isDesktop =>
      !kIsWeb && (Platform.isMacOS || Platform.isWindows || Platform.isLinux);

  // ── Permission helpers ──────────────────────────────────────────────

  /// Request camera permission. Returns true if granted.
  static Future<bool> requestCamera() async {
    if (isWeb) return true; // web handles via browser
    final status = await Permission.camera.request();
    return status.isGranted;
  }

  /// Request microphone permission. Returns true if granted.
  static Future<bool> requestMicrophone() async {
    if (isWeb) return true;
    final status = await Permission.microphone.request();
    return status.isGranted;
  }

  /// Request photo library permission. Returns true if granted.
  static Future<bool> requestPhotos() async {
    if (isWeb) return true;
    final status = await Permission.photos.request();
    return status.isGranted || status.isLimited;
  }

  /// Request storage permission (Android < 13 fallback). Returns true if granted.
  static Future<bool> requestStorage() async {
    if (isWeb || isIOS) return true;
    final status = await Permission.storage.request();
    return status.isGranted;
  }

  /// Check if camera is available.
  static Future<bool> get hasCameraPermission async {
    if (isWeb) return true;
    return await Permission.camera.isGranted;
  }

  /// Check if microphone is available.
  static Future<bool> get hasMicrophonePermission async {
    if (isWeb) return true;
    return await Permission.microphone.isGranted;
  }
}
