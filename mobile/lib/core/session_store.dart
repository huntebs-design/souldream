import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'api_client.dart';
import 'models.dart';

enum SessionPhase { loading, signedOut, signedIn }

class SessionStore extends ChangeNotifier {
  SessionStore({ApiClient? api, FlutterSecureStorage? storage})
    : api = api ?? ApiClient(),
      _storage = storage ?? const FlutterSecureStorage();

  static const _tokenKey = 'dilse_user_token';

  final ApiClient api;
  final FlutterSecureStorage _storage;

  SessionPhase phase = SessionPhase.loading;
  UserAccount? user;
  String? error;

  Future<void> restore() async {
    phase = SessionPhase.loading;
    notifyListeners();
    final savedToken = await _storage.read(key: _tokenKey);
    if (savedToken == null || savedToken.isEmpty) {
      phase = SessionPhase.signedOut;
      notifyListeners();
      return;
    }
    api.token = savedToken;
    try {
      user = await api.me();
      phase = SessionPhase.signedIn;
    } on ApiException catch (exception) {
      if (exception.statusCode == 401) {
        await _storage.delete(key: _tokenKey);
        api.token = null;
        user = null;
        phase = SessionPhase.signedOut;
      } else {
        error = exception.message;
        phase = SessionPhase.signedOut;
      }
    }
    notifyListeners();
  }

  Future<void> login(String email, String password) async {
    error = null;
    final payload = await api.login(email, password);
    await _saveAuth(payload);
  }

  Future<void> register({
    required String email,
    required String password,
    required String displayName,
    required String language,
  }) async {
    error = null;
    final payload = await api.register(
      email: email,
      password: password,
      displayName: displayName,
      language: language,
    );
    await _saveAuth(payload);
  }

  Future<void> _saveAuth(AuthPayload payload) async {
    api.token = payload.token;
    await _storage.write(key: _tokenKey, value: payload.token);
    user = payload.user;
    phase = SessionPhase.signedIn;
    notifyListeners();
  }

  Future<void> acceptTerms() async {
    user = await api.acceptTerms();
    notifyListeners();
  }

  Future<void> updateAccount({
    required String language,
    required int retentionDays,
  }) async {
    user = await api.updateAccount(
      language: language,
      retentionDays: retentionDays,
    );
    notifyListeners();
  }

  Future<void> setEmailNotifications(bool enabled) async {
    user = await api.updateEmailNotifications(enabled);
    notifyListeners();
  }

  Future<void> logout() async {
    try {
      await api.logout();
    } catch (_) {}
    await _clearLocalSession();
  }

  Future<void> deleteAccount(String password) async {
    await api.deleteAccount(password);
    await _clearLocalSession();
  }

  Future<void> _clearLocalSession() async {
    await _storage.delete(key: _tokenKey);
    api.token = null;
    user = null;
    phase = SessionPhase.signedOut;
    notifyListeners();
  }

  @override
  void dispose() {
    api.close();
    super.dispose();
  }
}
