import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

import 'api_client.dart';

@pragma('vm:entry-point')
Future<void> dilSeFirebaseBackgroundHandler(RemoteMessage message) async {
  if (!DilSeNotifications.isConfigured) return;
  if (Firebase.apps.isEmpty) {
    await Firebase.initializeApp(options: DilSeNotifications.firebaseOptions);
  }
}

class DilSeNotifications {
  DilSeNotifications(this.api);

  static const _apiKey = String.fromEnvironment('FIREBASE_API_KEY');
  static const _appId = String.fromEnvironment('FIREBASE_APP_ID');
  static const _senderId = String.fromEnvironment(
    'FIREBASE_MESSAGING_SENDER_ID',
  );
  static const _projectId = String.fromEnvironment('FIREBASE_PROJECT_ID');

  static bool get isConfigured =>
      _apiKey.isNotEmpty &&
      _appId.isNotEmpty &&
      _senderId.isNotEmpty &&
      _projectId.isNotEmpty;

  static FirebaseOptions get firebaseOptions => const FirebaseOptions(
    apiKey: _apiKey,
    appId: _appId,
    messagingSenderId: _senderId,
    projectId: _projectId,
  );

  static const _enabledKey = 'dilse_mobile_notifications_enabled';
  static const _deviceIdKey = 'dilse_mobile_device_id';
  static const _channel = AndroidNotificationChannel(
    'dilse_messages',
    'DilSe responses',
    description: 'Private alerts when a new DilSe response is waiting.',
    importance: Importance.high,
    playSound: true,
  );

  final ApiClient api;
  final FlutterLocalNotificationsPlugin _local =
      FlutterLocalNotificationsPlugin();
  StreamSubscription<String>? _tokenSubscription;
  StreamSubscription<RemoteMessage>? _messageSubscription;
  StreamSubscription<RemoteMessage>? _openedSubscription;
  void Function(String sessionId)? onSessionRequested;
  String? pendingSessionId;
  bool initialized = false;

  Future<void> initialize() async {
    if (!isConfigured || initialized) return;
    await Firebase.initializeApp(options: firebaseOptions);
    FirebaseMessaging.onBackgroundMessage(dilSeFirebaseBackgroundHandler);
    await _local.initialize(
      const InitializationSettings(
        android: AndroidInitializationSettings('@mipmap/ic_launcher'),
      ),
      onDidReceiveNotificationResponse: (response) {
        final sessionId = response.payload;
        if (sessionId != null && sessionId.isNotEmpty) {
          _openSession(sessionId);
        }
      },
    );
    await _local
        .resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin
        >()
        ?.createNotificationChannel(_channel);
    _messageSubscription = FirebaseMessaging.onMessage.listen((message) {
      final sessionId = message.data['session_id'];
      _local.show(
        message.hashCode,
        'DilSe',
        'A DilSe response is waiting for you.',
        const NotificationDetails(
          android: AndroidNotificationDetails(
            'dilse_messages',
            'DilSe responses',
            channelDescription:
                'Private alerts when a new DilSe response is waiting.',
            importance: Importance.high,
            priority: Priority.high,
            playSound: true,
            visibility: NotificationVisibility.private,
          ),
        ),
        payload: sessionId,
      );
    });
    _openedSubscription = FirebaseMessaging.onMessageOpenedApp.listen((
      message,
    ) {
      final sessionId = message.data['session_id'];
      if (sessionId != null && sessionId.isNotEmpty) _openSession(sessionId);
    });
    final initialMessage = await FirebaseMessaging.instance.getInitialMessage();
    final initialSession = initialMessage?.data['session_id'];
    if (initialSession != null && initialSession.isNotEmpty) {
      pendingSessionId = initialSession;
    }
    initialized = true;
  }

  void _openSession(String sessionId) {
    final handler = onSessionRequested;
    if (handler == null) {
      pendingSessionId = sessionId;
    } else {
      handler(sessionId);
    }
  }

  Future<bool> preferenceEnabled() async {
    final preferences = await SharedPreferences.getInstance();
    return preferences.getBool(_enabledKey) ?? true;
  }

  Future<String> _deviceId() async {
    final preferences = await SharedPreferences.getInstance();
    final existing = preferences.getString(_deviceIdKey);
    if (existing != null && existing.length >= 16) return existing;
    final created = const Uuid().v4().replaceAll('-', '_');
    await preferences.setString(_deviceIdKey, created);
    return created;
  }

  Future<void> recordAppPresence() async {
    try {
      final package = await PackageInfo.fromPlatform();
      await api.recordMobileInstallation(
        deviceId: await _deviceId(),
        appVersion: '${package.version}+${package.buildNumber}',
      );
    } catch (_) {}
  }

  Future<bool> enable() async {
    if (!isConfigured) return false;
    await initialize();
    final backendConfig = await api.mobilePushConfig();
    if (backendConfig['available'] != true) return false;
    final permission = await FirebaseMessaging.instance.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );
    if (permission.authorizationStatus != AuthorizationStatus.authorized &&
        permission.authorizationStatus != AuthorizationStatus.provisional) {
      return false;
    }
    final token = await FirebaseMessaging.instance.getToken();
    if (token == null || token.isEmpty) return false;
    final package = await PackageInfo.fromPlatform();
    final deviceId = await _deviceId();
    await api.registerMobileDevice(
      deviceId: deviceId,
      firebaseToken: token,
      appVersion: '${package.version}+${package.buildNumber}',
    );
    final preferences = await SharedPreferences.getInstance();
    await preferences.setBool(_enabledKey, true);
    await _tokenSubscription?.cancel();
    _tokenSubscription = FirebaseMessaging.instance.onTokenRefresh.listen((
      updatedToken,
    ) async {
      try {
        await api.registerMobileDevice(
          deviceId: deviceId,
          firebaseToken: updatedToken,
          appVersion: '${package.version}+${package.buildNumber}',
        );
      } catch (_) {}
    });
    return true;
  }

  Future<void> autoEnableForSignedInUser() async {
    try {
      await recordAppPresence();
    } catch (_) {}
    if (!await preferenceEnabled()) return;
    try {
      await enable();
    } catch (_) {}
  }

  Future<void> disable() async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.setBool(_enabledKey, false);
    try {
      await api.unregisterMobileDevice(await _deviceId());
    } catch (_) {}
    await _tokenSubscription?.cancel();
    _tokenSubscription = null;
  }

  Future<void> detachCurrentUser() async {
    try {
      await api.unregisterMobileDevice(await _deviceId());
    } catch (_) {}
    await _tokenSubscription?.cancel();
    _tokenSubscription = null;
  }

  Future<void> dispose() async {
    await _tokenSubscription?.cancel();
    await _messageSubscription?.cancel();
    await _openedSubscription?.cancel();
  }
}
