import 'dart:async';

import 'package:flutter/material.dart';

import '../core/models.dart';
import '../core/notification_service.dart';
import '../core/session_store.dart';
import '../core/theme.dart';
import '../core/update_service.dart';
import 'chat_screen.dart';
import 'history_screen.dart';
import 'new_chat_screen.dart';
import 'settings_screen.dart';

class MainShell extends StatefulWidget {
  const MainShell({
    super.key,
    required this.session,
    required this.notifications,
  });

  final SessionStore session;
  final DilSeNotifications notifications;

  @override
  State<MainShell> createState() => MainShellState();
}

class MainShellState extends State<MainShell> with WidgetsBindingObserver {
  final _historyKey = GlobalKey<HistoryScreenState>();
  int _index = 0;
  bool _checkedForUpdate = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    widget.notifications.onSessionRequested = openSessionById;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(widget.notifications.autoEnableForSignedInUser());
      final pending = widget.notifications.pendingSessionId;
      if (pending != null) {
        widget.notifications.pendingSessionId = null;
        unawaited(openSessionById(pending));
      }
      unawaited(_checkForUpdate());
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    widget.notifications.onSessionRequested = null;
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      unawaited(widget.notifications.recordAppPresence());
    }
  }

  Future<void> _checkForUpdate() async {
    if (_checkedForUpdate) return;
    _checkedForUpdate = true;
    try {
      final service = UpdateService(widget.session.api);
      final status = await service.check();
      if (!status.updateAvailable || !mounted) return;
      await showDialog<void>(
        context: context,
        barrierDismissible: !status.updateRequired,
        builder: (context) => PopScope(
          canPop: !status.updateRequired,
          child: AlertDialog(
            title: Text('DilSe ${status.release.latestVersion} is ready'),
            content: Text(status.release.releaseNotes),
            actions: [
              if (!status.updateRequired)
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Later'),
                ),
              FilledButton(
                onPressed: () async {
                  if (!status.updateRequired) Navigator.pop(context);
                  await service.openDownload(status.release.downloadUrl);
                },
                child: const Text('Download update'),
              ),
            ],
          ),
        ),
      );
    } catch (_) {}
  }

  void _startChat(ChatMode mode, PartnerConfig partner, String? starter) {
    Navigator.of(context)
        .push<void>(
          MaterialPageRoute(
            builder: (_) => ChatScreen(
              api: widget.session.api,
              mode: mode,
              initialPartner: partner,
              initialDraft: starter,
            ),
          ),
        )
        .then((_) => _historyKey.currentState?.refresh());
  }

  void _openChat(ChatSession session) {
    Navigator.of(context)
        .push<void>(
          MaterialPageRoute(
            builder: (_) => ChatScreen(
              api: widget.session.api,
              mode: session.mode,
              existingSession: session,
            ),
          ),
        )
        .then((_) => _historyKey.currentState?.refresh());
  }

  Future<void> openSessionById(String sessionId) async {
    try {
      final sessions = await widget.session.api.getSessions();
      final session = sessions
          .where((item) => item.sessionId == sessionId)
          .firstOrNull;
      if (session != null && mounted) _openChat(session);
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final screens = [
      NewChatScreen(
        displayName: widget.session.user!.displayName,
        onStart: _startChat,
      ),
      HistoryScreen(
        key: _historyKey,
        api: widget.session.api,
        onOpen: _openChat,
      ),
      SettingsScreen(
        session: widget.session,
        notifications: widget.notifications,
      ),
    ];
    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth >= 720;
        final content = IndexedStack(index: _index, children: screens);
        if (wide) {
          return Scaffold(
            body: Row(
              children: [
                SafeArea(
                  child: NavigationRail(
                    selectedIndex: _index,
                    onDestinationSelected: (value) =>
                        setState(() => _index = value),
                    labelType: NavigationRailLabelType.all,
                    backgroundColor: DilSeColours.paper,
                    indicatorColor: DilSeColours.petal,
                    destinations: const [
                      NavigationRailDestination(
                        icon: Icon(Icons.add_comment_outlined),
                        selectedIcon: Icon(Icons.add_comment_rounded),
                        label: Text('New chat'),
                      ),
                      NavigationRailDestination(
                        icon: Icon(Icons.chat_bubble_outline_rounded),
                        selectedIcon: Icon(Icons.chat_bubble_rounded),
                        label: Text('Chats'),
                      ),
                      NavigationRailDestination(
                        icon: Icon(Icons.settings_outlined),
                        selectedIcon: Icon(Icons.settings_rounded),
                        label: Text('Settings'),
                      ),
                    ],
                  ),
                ),
                const VerticalDivider(width: 1),
                Expanded(child: content),
              ],
            ),
          );
        }
        return Scaffold(
          body: content,
          bottomNavigationBar: NavigationBar(
            selectedIndex: _index,
            onDestinationSelected: (value) => setState(() => _index = value),
            backgroundColor: DilSeColours.paper,
            indicatorColor: DilSeColours.petal,
            destinations: const [
              NavigationDestination(
                icon: Icon(Icons.add_comment_outlined),
                selectedIcon: Icon(Icons.add_comment_rounded),
                label: 'New chat',
              ),
              NavigationDestination(
                icon: Icon(Icons.chat_bubble_outline_rounded),
                selectedIcon: Icon(Icons.chat_bubble_rounded),
                label: 'Chats',
              ),
              NavigationDestination(
                icon: Icon(Icons.settings_outlined),
                selectedIcon: Icon(Icons.settings_rounded),
                label: 'Settings',
              ),
            ],
          ),
        );
      },
    );
  }
}
