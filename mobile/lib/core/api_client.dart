import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import 'models.dart';

class ApiException implements Exception {
  const ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

class AuthPayload {
  const AuthPayload({required this.token, required this.user});

  final String token;
  final UserAccount user;

  factory AuthPayload.fromJson(Map<String, dynamic> json) => AuthPayload(
    token: json['token'] as String? ?? '',
    user: UserAccount.fromJson(json['user'] as Map<String, dynamic>),
  );
}

class ApiClient {
  ApiClient({
    this.baseUrl = const String.fromEnvironment(
      'DILSE_API_URL',
      defaultValue: 'https://www.baatdilse.com/api',
    ),
    http.Client? client,
  }) : _client = client ?? http.Client();

  final String baseUrl;
  final http.Client _client;
  String? token;

  Map<String, String> get _headers => {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    if (token != null && token!.isNotEmpty) 'X-User-Token': token!,
  };

  Uri _uri(String path, [Map<String, dynamic>? query]) {
    final uri = Uri.parse('$baseUrl$path');
    if (query == null) return uri;
    return uri.replace(
      queryParameters: query.map((key, value) => MapEntry(key, '$value')),
    );
  }

  Future<dynamic> _request(
    String method,
    String path, {
    Map<String, dynamic>? body,
    Map<String, dynamic>? query,
    Duration timeout = const Duration(seconds: 45),
  }) async {
    late http.Response response;
    try {
      final uri = _uri(path, query);
      final encoded = body == null ? null : jsonEncode(body);
      response = switch (method) {
        'GET' => await _client.get(uri, headers: _headers).timeout(timeout),
        'POST' =>
          await _client
              .post(uri, headers: _headers, body: encoded)
              .timeout(timeout),
        'PUT' =>
          await _client
              .put(uri, headers: _headers, body: encoded)
              .timeout(timeout),
        'DELETE' =>
          await _client
              .delete(uri, headers: _headers, body: encoded)
              .timeout(timeout),
        _ => throw const ApiException('Unsupported request.'),
      };
    } on ApiException {
      rethrow;
    } catch (_) {
      throw const ApiException(
        'DilSe could not connect. Check your internet connection and try again.',
      );
    }
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.bodyBytes.isEmpty) return null;
      try {
        return jsonDecode(utf8.decode(response.bodyBytes));
      } catch (_) {
        return utf8.decode(response.bodyBytes);
      }
    }
    throw ApiException(
      _errorMessage(response),
      statusCode: response.statusCode,
    );
  }

  String _errorMessage(http.Response response) {
    try {
      final decoded = jsonDecode(utf8.decode(response.bodyBytes));
      final detail = decoded is Map<String, dynamic> ? decoded['detail'] : null;
      if (detail is String && detail.trim().isNotEmpty) return detail;
      if (detail is List && detail.isNotEmpty) {
        final first = detail.first;
        if (first is Map<String, dynamic>) {
          return first['msg'] as String? ??
              'Check the information and try again.';
        }
      }
    } catch (_) {}
    return switch (response.statusCode) {
      401 => 'Your sign-in has expired. Sign in again.',
      404 => 'That conversation could not be found.',
      429 => 'DilSe is receiving many messages. Wait a moment and try again.',
      _ => 'DilSe could not complete that request.',
    };
  }

  Future<AuthPayload> login(String email, String password) async {
    final json = await _request(
      'POST',
      '/auth/login',
      body: {'email': email.trim(), 'password': password},
    ) as Map<String, dynamic>;
    return AuthPayload.fromJson(json);
  }

  Future<AuthPayload> register({
    required String email,
    required String password,
    required String displayName,
    required String language,
  }) async {
    final json = await _request(
      'POST',
      '/auth/register',
      body: {
        'email': email.trim(),
        'password': password,
        'display_name': displayName.trim(),
        'language': language,
        'country': 'Pakistan',
        'terms_accepted': true,
      },
    ) as Map<String, dynamic>;
    return AuthPayload.fromJson(json);
  }

  Future<UserAccount> me() async => UserAccount.fromJson(
    await _request('GET', '/auth/me') as Map<String, dynamic>,
  );

  Future<void> logout() => _request('POST', '/auth/logout');

  Future<UserAccount> acceptTerms() async => UserAccount.fromJson(
    await _request('PUT', '/account/terms', body: {'terms_accepted': true})
        as Map<String, dynamic>,
  );

  Future<UserAccount> updateAccount({
    required String language,
    required int retentionDays,
  }) async => UserAccount.fromJson(
    await _request(
      'PUT',
      '/account/privacy',
      body: {
        'language': language,
        'country': 'Pakistan',
        'retention_days': retentionDays,
        'allow_admin_review': true,
        'allow_admin_intervention': true,
        'store_chats': true,
      },
    ) as Map<String, dynamic>,
  );

  Future<UserAccount> updateEmailNotifications(bool enabled) async =>
      UserAccount.fromJson(
        await _request(
          'PUT',
          '/account/notifications',
          body: {'enabled': enabled},
        ) as Map<String, dynamic>,
      );

  Future<void> deleteAccount(String password) =>
      _request('DELETE', '/account', body: {'password': password});

  Future<Catalog> getCatalog() async => Catalog.fromJson(
    await _request('GET', '/catalog') as Map<String, dynamic>,
  );

  Future<List<ChatSession>> getSessions() async =>
      (await _request('GET', '/sessions') as List<dynamic>)
          .map((item) => ChatSession.fromJson(item as Map<String, dynamic>))
          .toList();

  Future<List<ChatMessage>> getMessages(String sessionId) async =>
      (await _request('GET', '/sessions/$sessionId/messages') as List<dynamic>)
          .map((item) => ChatMessage.fromJson(item as Map<String, dynamic>))
          .toList();

  Future<ChatResult> sendMessage({
    required String sessionId,
    required String message,
    required ChatMode mode,
    required PartnerConfig partner,
    int? replyToMessageId,
  }) async {
    final body = <String, dynamic>{
      'session_id': sessionId,
      'message': message,
      'mode': mode.apiValue,
      'client_platform': 'android_app',
      if (mode == ChatMode.partner) ...{
        if (partner.scenario != null) 'scenario': partner.scenario,
        if (partner.persona != null) 'persona': partner.persona,
        'roleplay_intensity': partner.intensity,
        'roleplay_difficulty': partner.difficulty,
        if (partner.characterDescription.trim().isNotEmpty)
          'character_description': partner.characterDescription.trim(),
      },
    };
    if (replyToMessageId != null) {
      body['reply_to_message_id'] = replyToMessageId;
    }
    return ChatResult.fromJson(
      await _request(
        'POST',
        '/chat',
        body: body,
        timeout: const Duration(seconds: 120),
      ) as Map<String, dynamic>,
    );
  }

  Future<Map<String, dynamic>> sendVoiceNote({
    required String sessionId,
    required Uint8List audioBytes,
    required String uploadId,
    required ChatMode mode,
    required PartnerConfig partner,
    int? replyToMessageId,
  }) async {
    final body = <String, dynamic>{
      'audio_base64': base64Encode(audioBytes),
      'audio_mime_type': 'audio/wav',
      'audio_filename': 'voice-note.wav',
      'upload_id': uploadId,
      'mode': mode.apiValue,
      'client_platform': 'android_app',
      if (mode == ChatMode.partner) ...{
        if (partner.scenario != null) 'scenario': partner.scenario,
        if (partner.persona != null) 'persona': partner.persona,
        'roleplay_intensity': partner.intensity,
        'roleplay_difficulty': partner.difficulty,
        if (partner.characterDescription.trim().isNotEmpty)
          'character_description': partner.characterDescription.trim(),
      },
    };
    if (replyToMessageId != null) {
      body['reply_to_message_id'] = replyToMessageId;
    }
    return await _request(
      'POST',
      '/sessions/$sessionId/voice-notes',
      body: body,
      timeout: const Duration(seconds: 120),
    ) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> sync(String sessionId, int afterId) async =>
      await _request(
        'GET',
        '/sessions/$sessionId/sync',
        query: {'after_id': afterId},
      ) as Map<String, dynamic>;

  Future<void> updateTyping(String sessionId, bool isTyping) => _request(
    'POST',
    '/sessions/$sessionId/typing',
    body: {'is_typing': isTyping},
  );

  Future<void> markRead(String sessionId, List<int> messageIds) async {
    if (messageIds.isEmpty) return;
    await _request(
      'POST',
      '/sessions/$sessionId/read',
      body: {'message_ids': messageIds},
    );
  }

  Future<void> deleteSession(String sessionId) =>
      _request('DELETE', '/sessions/$sessionId');

  Future<Map<String, dynamic>?> getConversationState(String sessionId) async {
    try {
      return await _request('GET', '/sessions/$sessionId/state')
          as Map<String, dynamic>;
    } on ApiException catch (error) {
      if (error.statusCode == 404) return null;
      rethrow;
    }
  }

  Future<void> confirmConversationState(String sessionId, String summary) =>
      _request('PUT', '/sessions/$sessionId/state', body: {'summary': summary});

  Future<void> reportMessage(int messageId, String category, {String? notes}) {
    final body = <String, dynamic>{'category': category};
    if (notes != null) body['notes'] = notes;
    return _request('POST', '/messages/$messageId/feedback', body: body);
  }

  String attachmentUrl(int messageId) =>
      '$baseUrl/messages/$messageId/attachment';

  String voiceNoteUrl(int messageId) =>
      '$baseUrl/messages/$messageId/voice-note';

  Map<String, String> get mediaHeaders => {
    if (token != null && token!.isNotEmpty) 'X-User-Token': token!,
  };

  Future<Uint8List> getVoiceNote(int messageId) async {
    late http.Response response;
    try {
      response = await _client
          .get(_uri('/messages/$messageId/voice-note'), headers: mediaHeaders)
          .timeout(const Duration(seconds: 60));
    } catch (_) {
      throw const ApiException('The voice note could not be downloaded.');
    }
    if (response.statusCode != 200) {
      throw ApiException(
        _errorMessage(response),
        statusCode: response.statusCode,
      );
    }
    return response.bodyBytes;
  }

  Future<Map<String, dynamic>> mobilePushConfig() async =>
      await _request('GET', '/account/mobile-push/config')
          as Map<String, dynamic>;

  Future<void> recordMobileInstallation({
    required String deviceId,
    required String appVersion,
  }) => _request(
    'PUT',
    '/account/mobile-installation',
    body: {'device_id': deviceId, 'app_version': appVersion},
  );

  Future<void> registerMobileDevice({
    required String deviceId,
    required String firebaseToken,
    required String appVersion,
  }) => _request(
    'POST',
    '/account/mobile-push/devices',
    body: {
      'device_id': deviceId,
      'token': firebaseToken,
      'app_version': appVersion,
    },
  );

  Future<void> unregisterMobileDevice(String deviceId) => _request(
    'POST',
    '/account/mobile-push/unregister',
    body: {'device_id': deviceId},
  );

  Future<MobileRelease> getMobileRelease() async => MobileRelease.fromJson(
    await _request('GET', '/mobile/version') as Map<String, dynamic>,
  );

  void close() => _client.close();
}
