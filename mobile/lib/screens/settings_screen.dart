import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/api_client.dart';
import '../core/notification_service.dart';
import '../core/session_store.dart';
import '../core/theme.dart';
import '../core/update_service.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({
    super.key,
    required this.session,
    required this.notifications,
  });

  final SessionStore session;
  final DilSeNotifications notifications;

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late String _language;
  late int _retention;
  late bool _emailNotifications;
  bool _phoneNotifications = true;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    final user = widget.session.user!;
    _language = user.language;
    _retention = user.retentionDays;
    _emailNotifications = user.emailNotificationsEnabled;
    widget.notifications.preferenceEnabled().then((value) {
      if (mounted) setState(() => _phoneNotifications = value);
    });
  }

  Future<void> _saveProfile() async {
    setState(() => _saving = true);
    try {
      await widget.session.updateAccount(
        language: _language,
        retentionDays: _retention,
      );
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text('Settings saved.')));
      }
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _setEmailNotifications(bool enabled) async {
    setState(() => _emailNotifications = enabled);
    try {
      await widget.session.setEmailNotifications(enabled);
    } on ApiException catch (error) {
      if (mounted) {
        setState(() => _emailNotifications = !enabled);
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    }
  }

  Future<void> _setPhoneNotifications(bool enabled) async {
    setState(() => _phoneNotifications = enabled);
    try {
      if (enabled) {
        final registered = await widget.notifications.enable();
        if (!registered) {
          throw const ApiException(
            'Phone notifications are unavailable or permission was not granted.',
          );
        }
      } else {
        await widget.notifications.disable();
      }
    } on ApiException catch (error) {
      if (mounted) {
        setState(() => _phoneNotifications = !enabled);
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    }
  }

  Future<void> _checkForUpdate() async {
    try {
      final service = UpdateService(widget.session.api);
      final status = await service.check();
      if (!mounted) return;
      if (!status.updateAvailable) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('You have the latest DilSe version.')),
        );
        return;
      }
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text('DilSe ${status.release.latestVersion} is available'),
          content: Text(status.release.releaseNotes),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Later'),
            ),
            FilledButton(
              onPressed: () async {
                Navigator.pop(context);
                await service.openDownload(status.release.downloadUrl);
              },
              child: const Text('Download update'),
            ),
          ],
        ),
      );
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    }
  }

  Future<void> _deleteAccount() async {
    final controller = TextEditingController();
    final password = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Permanently delete your account?'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Your account and stored conversations will be removed. Enter your password to continue.',
            ),
            const SizedBox(height: 16),
            TextField(
              controller: controller,
              obscureText: true,
              decoration: const InputDecoration(labelText: 'Password'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text),
            style: FilledButton.styleFrom(
              backgroundColor: const Color(0xFF9D2D3F),
            ),
            child: const Text('Delete account'),
          ),
        ],
      ),
    );
    controller.dispose();
    if (password == null || password.isEmpty) return;
    try {
      await widget.notifications.disable();
      await widget.session.deleteAccount(password);
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = widget.session.user!;
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(18, 4, 18, 100),
        children: [
          _SettingsCard(
            child: ListTile(
              contentPadding: const EdgeInsets.all(16),
              leading: CircleAvatar(
                backgroundColor: DilSeColours.petal,
                foregroundColor: DilSeColours.mulberry,
                child: Text(user.displayName[0].toUpperCase()),
              ),
              title: Text(
                user.displayName,
                style: const TextStyle(fontWeight: FontWeight.w800),
              ),
              subtitle: Text(user.email),
            ),
          ),
          const _SectionLabel('CONVERSATION'),
          _SettingsCard(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  DropdownButtonFormField<String>(
                    initialValue: _language,
                    decoration: const InputDecoration(labelText: 'Language'),
                    items:
                        const [
                              'English',
                              'Urdu',
                              'Roman Urdu',
                              'English and Urdu',
                            ]
                            .map(
                              (value) => DropdownMenuItem(
                                value: value,
                                child: Text(value),
                              ),
                            )
                            .toList(),
                    onChanged: (value) =>
                        setState(() => _language = value ?? _language),
                  ),
                  const SizedBox(height: 14),
                  DropdownButtonFormField<int>(
                    initialValue: _retention,
                    decoration: const InputDecoration(
                      labelText: 'Keep conversation history',
                    ),
                    items: const [7, 30, 90, 180, 365]
                        .map(
                          (days) => DropdownMenuItem(
                            value: days,
                            child: Text('$days days'),
                          ),
                        )
                        .toList(),
                    onChanged: (value) =>
                        setState(() => _retention = value ?? _retention),
                  ),
                  const SizedBox(height: 15),
                  FilledButton(
                    onPressed: _saving ? null : _saveProfile,
                    child: Text(_saving ? 'Saving…' : 'Save changes'),
                  ),
                ],
              ),
            ),
          ),
          const _SectionLabel('NOTIFICATIONS'),
          _SettingsCard(
            child: Column(
              children: [
                SwitchListTile(
                  value: _phoneNotifications,
                  onChanged: _setPhoneNotifications,
                  secondary: const Icon(Icons.notifications_active_outlined),
                  title: const Text('Phone notifications'),
                  subtitle: const Text(
                    'Play a private alert for a new DilSe response.',
                  ),
                ),
                const Divider(height: 1),
                SwitchListTile(
                  value: _emailNotifications,
                  onChanged: _setEmailNotifications,
                  secondary: const Icon(Icons.mail_outline_rounded),
                  title: const Text('Email reminders'),
                  subtitle: const Text(
                    'Email me if a DilSe response remains unread.',
                  ),
                ),
              ],
            ),
          ),
          const _SectionLabel('ACCOUNT'),
          _SettingsCard(
            child: Column(
              children: [
                ListTile(
                  leading: const Icon(Icons.description_outlined),
                  title: const Text('Terms and Conditions'),
                  trailing: const Icon(Icons.open_in_new_rounded, size: 19),
                  onTap: () => launchUrl(
                    Uri.parse('https://www.baatdilse.com/app/?page=terms'),
                    mode: LaunchMode.externalApplication,
                  ),
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(Icons.system_update_alt_rounded),
                  title: const Text('Check for updates'),
                  onTap: _checkForUpdate,
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(Icons.logout_rounded),
                  title: const Text('Sign out'),
                  onTap: () async {
                    await widget.notifications.detachCurrentUser();
                    await widget.session.logout();
                  },
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(
                    Icons.delete_outline,
                    color: Color(0xFF9D2D3F),
                  ),
                  title: const Text(
                    'Delete account',
                    style: TextStyle(color: Color(0xFF9D2D3F)),
                  ),
                  onTap: _deleteAccount,
                ),
              ],
            ),
          ),
          const SizedBox(height: 22),
          Text(
            'DilSe provides relationship guidance and practice. It is not licensed therapy, legal advice or an emergency service.',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodySmall
                ?.copyWith(color: DilSeColours.muted, height: 1.5),
          ),
        ],
      ),
    );
  }
}

class _SettingsCard extends StatelessWidget {
  const _SettingsCard({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) => Card(child: child);
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(6, 27, 6, 9),
    child: Text(
      text,
      style: Theme.of(context).textTheme.labelSmall?.copyWith(
        color: DilSeColours.raspberry,
        letterSpacing: 1.2,
        fontWeight: FontWeight.w800,
      ),
    ),
  );
}
