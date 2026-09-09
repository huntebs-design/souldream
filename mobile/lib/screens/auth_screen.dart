import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/api_client.dart';
import '../core/session_store.dart';
import '../core/theme.dart';
import '../widgets/brand.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key, required this.session});

  final SessionStore session;

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _creating = false;
  bool _agreed = false;
  bool _obscure = true;
  bool _loading = false;
  String _language = 'English';
  String? _error;

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_creating && !_agreed) {
      setState(() => _error = 'Agree to the Terms and Conditions to continue.');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      if (_creating) {
        await widget.session.register(
          email: _email.text,
          password: _password.text,
          displayName: _name.text,
          language: _language,
        );
      } else {
        await widget.session.login(_email.text, _password.text);
      }
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _openTerms() async {
    await launchUrl(
      Uri.parse('https://www.baatdilse.com/app/?page=terms'),
      mode: LaunchMode.externalApplication,
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: PetalBackdrop(
      child: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(22, 28, 22, 42),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 460),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const DilSeWordmark(height: 48),
                  const SizedBox(height: 34),
                  Text(
                    _creating
                        ? 'Make room for the words you need.'
                        : 'Continue your conversation.',
                    style: Theme.of(context).textTheme.displayLarge,
                  ),
                  const SizedBox(height: 12),
                  Text(
                    _creating
                        ? 'A private conversation space for adults 18+ in Pakistan.'
                        : 'Sign in with the email connected to your DilSe account.',
                    style: Theme.of(context).textTheme.bodyLarge
                        ?.copyWith(color: DilSeColours.muted),
                  ),
                  const SizedBox(height: 28),
                  Container(
                    padding: const EdgeInsets.all(5),
                    decoration: BoxDecoration(
                      color: DilSeColours.petal,
                      borderRadius: BorderRadius.circular(18),
                    ),
                    child: Row(
                      children: [
                        _ModeTab(
                          label: 'Sign in',
                          selected: !_creating,
                          onTap: () => setState(() {
                            _creating = false;
                            _error = null;
                          }),
                        ),
                        _ModeTab(
                          label: 'Create account',
                          selected: _creating,
                          onTap: () => setState(() {
                            _creating = true;
                            _error = null;
                          }),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),
                  Form(
                    key: _formKey,
                    child: AnimatedSize(
                      duration: const Duration(milliseconds: 220),
                      alignment: Alignment.topCenter,
                      child: Column(
                        children: [
                          if (_creating) ...[
                            TextFormField(
                              controller: _name,
                              textInputAction: TextInputAction.next,
                              textCapitalization: TextCapitalization.words,
                              autofillHints: const [AutofillHints.name],
                              decoration: const InputDecoration(
                                labelText: 'Name or nickname',
                              ),
                              validator: (value) =>
                                  value == null || value.trim().isEmpty
                                  ? 'Enter a name or nickname.'
                                  : null,
                            ),
                            const SizedBox(height: 14),
                          ],
                          TextFormField(
                            controller: _email,
                            keyboardType: TextInputType.emailAddress,
                            textInputAction: TextInputAction.next,
                            autofillHints: const [AutofillHints.email],
                            decoration: const InputDecoration(
                              labelText: 'Email',
                            ),
                            validator: (value) =>
                                value == null ||
                                    !value.contains('@') ||
                                    !value.contains('.')
                                ? 'Enter a valid email address.'
                                : null,
                          ),
                          const SizedBox(height: 14),
                          TextFormField(
                            controller: _password,
                            obscureText: _obscure,
                            textInputAction: TextInputAction.done,
                            autofillHints: _creating
                                ? const [AutofillHints.newPassword]
                                : const [AutofillHints.password],
                            onFieldSubmitted: (_) => _submit(),
                            decoration: InputDecoration(
                              labelText: 'Password',
                              suffixIcon: IconButton(
                                tooltip: _obscure
                                    ? 'Show password'
                                    : 'Hide password',
                                onPressed: () =>
                                    setState(() => _obscure = !_obscure),
                                icon: Icon(
                                  _obscure
                                      ? Icons.visibility_outlined
                                      : Icons.visibility_off_outlined,
                                ),
                              ),
                            ),
                            validator: (value) =>
                                value == null || value.length < 10
                                ? 'Use at least 10 characters.'
                                : null,
                          ),
                          if (_creating) ...[
                            const SizedBox(height: 14),
                            DropdownButtonFormField<String>(
                              initialValue: _language,
                              decoration: const InputDecoration(
                                labelText: 'Preferred language',
                              ),
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
                              onChanged: (value) => setState(
                                () => _language = value ?? 'English',
                              ),
                            ),
                            const SizedBox(height: 12),
                            CheckboxListTile(
                              value: _agreed,
                              onChanged: (value) =>
                                  setState(() => _agreed = value ?? false),
                              controlAffinity: ListTileControlAffinity.leading,
                              contentPadding: EdgeInsets.zero,
                              activeColor: DilSeColours.mulberry,
                              title: const Text(
                                'I Agree with the Terms and Conditions',
                                style: TextStyle(fontWeight: FontWeight.w600),
                              ),
                              subtitle: Align(
                                alignment: Alignment.centerLeft,
                                child: TextButton(
                                  onPressed: _openTerms,
                                  child: const Text(
                                    'Read the Terms and Conditions',
                                  ),
                                ),
                              ),
                            ),
                          ],
                          if (_error != null) ...[
                            const SizedBox(height: 8),
                            Align(
                              alignment: Alignment.centerLeft,
                              child: Text(
                                _error!,
                                style: const TextStyle(
                                  color: Color(0xFF9D2D3F),
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ],
                          const SizedBox(height: 18),
                          FilledButton(
                            onPressed: _loading ? null : _submit,
                            child: _loading
                                ? const SizedBox.square(
                                    dimension: 21,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2.2,
                                      color: Colors.white,
                                    ),
                                  )
                                : Text(
                                    _creating
                                        ? 'Create private account'
                                        : 'Sign in',
                                  ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 22),
                  Text(
                    'DilSe provides relationship guidance and practice. It is not licensed therapy or an emergency service.',
                    style: Theme.of(context).textTheme.bodySmall
                        ?.copyWith(color: DilSeColours.muted, height: 1.5),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    ),
  );
}

class _ModeTab extends StatelessWidget {
  const _ModeTab({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Expanded(
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          color: selected ? Colors.white : Colors.transparent,
          borderRadius: BorderRadius.circular(14),
          boxShadow: selected
              ? [
                  BoxShadow(
                    color: DilSeColours.mulberry.withValues(alpha: .08),
                    blurRadius: 12,
                  ),
                ]
              : null,
        ),
        child: Text(
          label,
          textAlign: TextAlign.center,
          style: TextStyle(
            color: DilSeColours.mulberry,
            fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
          ),
        ),
      ),
    ),
  );
}
