import 'dart:async';

import 'package:flutter/material.dart';

import 'core/notification_service.dart';
import 'core/session_store.dart';
import 'core/theme.dart';
import 'screens/auth_screen.dart';
import 'screens/main_shell.dart';
import 'screens/terms_update_screen.dart';
import 'widgets/brand.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final session = SessionStore();
  final notifications = DilSeNotifications(session.api);
  if (DilSeNotifications.isConfigured) {
    try {
      await notifications.initialize();
    } catch (_) {}
  }
  runApp(DilSeApp(session: session, notifications: notifications));
  unawaited(session.restore());
}

class DilSeApp extends StatelessWidget {
  const DilSeApp({
    super.key,
    required this.session,
    required this.notifications,
  });

  final SessionStore session;
  final DilSeNotifications notifications;

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'DilSe',
    debugShowCheckedModeBanner: false,
    theme: buildDilSeTheme(),
    home: AnimatedBuilder(
      animation: session,
      builder: (context, _) {
        if (session.phase == SessionPhase.loading) {
          return const _LoadingScreen();
        }
        if (session.phase == SessionPhase.signedOut || session.user == null) {
          return AuthScreen(session: session);
        }
        if (session.user!.requiresTermsAcceptance) {
          return TermsUpdateScreen(session: session);
        }
        return MainShell(session: session, notifications: notifications);
      },
    ),
  );
}

class _LoadingScreen extends StatelessWidget {
  const _LoadingScreen();

  @override
  Widget build(BuildContext context) => const Scaffold(
    body: PetalBackdrop(
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            DilSeMark(size: 72),
            SizedBox(height: 22),
            SizedBox.square(
              dimension: 22,
              child: CircularProgressIndicator(strokeWidth: 2.2),
            ),
          ],
        ),
      ),
    ),
  );
}
