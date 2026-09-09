import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/api_client.dart';
import '../core/session_store.dart';
import '../core/theme.dart';
import '../widgets/brand.dart';

class TermsUpdateScreen extends StatefulWidget {
  const TermsUpdateScreen({super.key, required this.session});

  final SessionStore session;

  @override
  State<TermsUpdateScreen> createState() => _TermsUpdateScreenState();
}

class _TermsUpdateScreenState extends State<TermsUpdateScreen> {
  bool agreed = false;
  bool loading = false;
  String? error;

  Future<void> _accept() async {
    if (!agreed) return;
    setState(() {
      loading = true;
      error = null;
    });
    try {
      await widget.session.acceptTerms();
    } on ApiException catch (exception) {
      if (mounted) setState(() => error = exception.message);
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: PetalBackdrop(
      child: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 480),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const DilSeMark(size: 48),
                      const SizedBox(height: 24),
                      Text(
                        'Review the updated Terms',
                        style: Theme.of(context).textTheme.headlineLarge,
                      ),
                      const SizedBox(height: 12),
                      Text(
                        'Read the full Terms and Conditions before continuing your conversations.',
                        style: Theme.of(context).textTheme.bodyLarge
                            ?.copyWith(color: DilSeColours.muted),
                      ),
                      const SizedBox(height: 14),
                      TextButton.icon(
                        onPressed: () => launchUrl(
                          Uri.parse(
                            'https://www.baatdilse.com/app/?page=terms',
                          ),
                          mode: LaunchMode.externalApplication,
                        ),
                        icon: const Icon(Icons.open_in_new_rounded),
                        label: const Text('Open the Terms and Conditions'),
                      ),
                      CheckboxListTile(
                        value: agreed,
                        onChanged: (value) =>
                            setState(() => agreed = value ?? false),
                        controlAffinity: ListTileControlAffinity.leading,
                        contentPadding: EdgeInsets.zero,
                        activeColor: DilSeColours.mulberry,
                        title: const Text(
                          'I Agree with the Terms and Conditions',
                          style: TextStyle(fontWeight: FontWeight.w700),
                        ),
                      ),
                      if (error != null)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: Text(
                            error!,
                            style: const TextStyle(color: Color(0xFF9D2D3F)),
                          ),
                        ),
                      FilledButton(
                        onPressed: !agreed || loading ? null : _accept,
                        child: loading
                            ? const SizedBox.square(
                                dimension: 20,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Colors.white,
                                ),
                              )
                            : const Text('Accept and continue'),
                      ),
                      const SizedBox(height: 8),
                      TextButton(
                        onPressed: loading ? null : widget.session.logout,
                        child: const Text('Sign out'),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    ),
  );
}
