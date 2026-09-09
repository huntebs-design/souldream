enum ChatMode { listener, partner }

extension ChatModeValue on ChatMode {
  String get apiValue => name;
  String get label => this == ChatMode.listener ? 'Listener' : 'Partner';
}

class UserAccount {
  const UserAccount({
    required this.id,
    required this.email,
    required this.displayName,
    required this.language,
    required this.country,
    required this.retentionDays,
    required this.emailNotificationsEnabled,
    required this.requiresTermsAcceptance,
    required this.createdAt,
  });

  final int id;
  final String email;
  final String displayName;
  final String language;
  final String country;
  final int retentionDays;
  final bool emailNotificationsEnabled;
  final bool requiresTermsAcceptance;
  final DateTime? createdAt;

  factory UserAccount.fromJson(Map<String, dynamic> json) => UserAccount(
    id: json['id'] as int,
    email: json['email'] as String? ?? '',
    displayName: json['display_name'] as String? ?? 'DilSe user',
    language: json['language'] as String? ?? 'English',
    country: json['country'] as String? ?? 'Pakistan',
    retentionDays: json['retention_days'] as int? ?? 30,
    emailNotificationsEnabled:
        json['email_notifications_enabled'] as bool? ?? true,
    requiresTermsAcceptance:
        json['requires_terms_acceptance'] as bool? ?? false,
    createdAt: DateTime.tryParse(json['created_at'] as String? ?? ''),
  );
}

class CatalogItem {
  const CatalogItem({
    required this.slug,
    required this.name,
    required this.description,
    this.starter,
  });

  final String slug;
  final String name;
  final String description;
  final String? starter;

  factory CatalogItem.fromJson(Map<String, dynamic> json) => CatalogItem(
    slug: json['slug'] as String? ?? '',
    name: json['name'] as String? ?? '',
    description: json['description'] as String? ?? '',
    starter: json['starter'] as String?,
  );
}

class Catalog {
  const Catalog({
    required this.personas,
    required this.scenarios,
    required this.exercises,
    required this.cards,
  });

  final List<CatalogItem> personas;
  final List<CatalogItem> scenarios;
  final List<CatalogItem> exercises;
  final List<CatalogItem> cards;

  factory Catalog.fromJson(Map<String, dynamic> json) {
    List<CatalogItem> items(String key) => (json[key] as List<dynamic>? ?? [])
        .map((item) => CatalogItem.fromJson(item as Map<String, dynamic>))
        .toList();
    return Catalog(
      personas: items('personas'),
      scenarios: items('scenarios'),
      exercises: items('exercises'),
      cards: items('cards'),
    );
  }

  static const empty = Catalog(
    personas: [],
    scenarios: [],
    exercises: [],
    cards: [],
  );
}

class PartnerConfig {
  const PartnerConfig({
    this.scenario,
    this.persona,
    this.intensity = 'explicit',
    this.difficulty = 'realistic',
    this.characterDescription = '',
  });

  final String? scenario;
  final String? persona;
  final String intensity;
  final String difficulty;
  final String characterDescription;

  PartnerConfig copyWith({
    String? scenario,
    String? persona,
    String? intensity,
    String? difficulty,
    String? characterDescription,
  }) => PartnerConfig(
    scenario: scenario ?? this.scenario,
    persona: persona ?? this.persona,
    intensity: intensity ?? this.intensity,
    difficulty: difficulty ?? this.difficulty,
    characterDescription: characterDescription ?? this.characterDescription,
  );
}

class ChatSession {
  const ChatSession({
    required this.sessionId,
    required this.mode,
    required this.lastActivity,
    required this.messageCount,
    required this.preview,
    this.scenario,
    this.character,
    this.intensity,
    this.difficulty,
    this.characterDescription,
  });

  final String sessionId;
  final ChatMode mode;
  final DateTime? lastActivity;
  final int messageCount;
  final String preview;
  final String? scenario;
  final String? character;
  final String? intensity;
  final String? difficulty;
  final String? characterDescription;

  factory ChatSession.fromJson(Map<String, dynamic> json) => ChatSession(
    sessionId: json['session_id'] as String? ?? '',
    mode: json['mode'] == 'partner' ? ChatMode.partner : ChatMode.listener,
    lastActivity: DateTime.tryParse(json['last_activity'] as String? ?? ''),
    messageCount: json['message_count'] as int? ?? 0,
    preview: json['first_user_message'] as String? ?? 'Conversation',
    scenario: json['scenario'] as String?,
    character: json['character'] as String?,
    intensity: json['roleplay_intensity'] as String?,
    difficulty: json['roleplay_difficulty'] as String?,
    characterDescription: json['character_description'] as String?,
  );

  PartnerConfig get partnerConfig => PartnerConfig(
    scenario: scenario,
    persona: character,
    intensity: intensity ?? 'explicit',
    difficulty: difficulty ?? 'realistic',
    characterDescription: characterDescription ?? '',
  );
}

class ChatMessage {
  const ChatMessage({
    required this.id,
    required this.role,
    required this.content,
    required this.source,
    required this.createdAt,
    this.replyToMessageId,
    this.replyToContent,
    this.attachmentId,
    this.attachmentFilename,
    this.voiceNoteId,
    this.voiceNoteFilename,
    this.voiceDuration,
    this.pending = false,
  });

  final int id;
  final String role;
  final String content;
  final String source;
  final DateTime? createdAt;
  final int? replyToMessageId;
  final String? replyToContent;
  final int? attachmentId;
  final String? attachmentFilename;
  final int? voiceNoteId;
  final String? voiceNoteFilename;
  final double? voiceDuration;
  final bool pending;

  bool get isUser => role == 'user';
  bool get hasAttachment => attachmentId != null;
  bool get hasVoiceNote => voiceNoteId != null;

  factory ChatMessage.fromJson(Map<String, dynamic> json) => ChatMessage(
    id: json['id'] as int? ?? 0,
    role: json['role'] as String? ?? 'assistant',
    content: json['content'] as String? ?? '',
    source: json['source'] as String? ?? 'ai',
    createdAt: DateTime.tryParse(json['created_at'] as String? ?? ''),
    replyToMessageId: json['reply_to_message_id'] as int?,
    replyToContent: json['reply_to_content'] as String?,
    attachmentId: json['attachment_id'] as int?,
    attachmentFilename: json['attachment_filename'] as String?,
    voiceNoteId: json['voice_note_id'] as int?,
    voiceNoteFilename: json['voice_note_filename'] as String?,
    voiceDuration: (json['voice_note_duration_seconds'] as num?)?.toDouble(),
  );
}

class ChatResult {
  const ChatResult({
    required this.response,
    required this.delivery,
    this.messageId,
    this.userMessageId,
    this.checkpoint,
  });

  final String response;
  final String delivery;
  final int? messageId;
  final int? userMessageId;
  final Map<String, dynamic>? checkpoint;

  factory ChatResult.fromJson(Map<String, dynamic> json) => ChatResult(
    response: json['response'] as String? ?? '',
    delivery: json['delivery'] as String? ?? 'ai',
    messageId: json['message_id'] as int?,
    userMessageId: json['user_message_id'] as int?,
    checkpoint: json['conversation_checkpoint'] as Map<String, dynamic>?,
  );
}

class MobileRelease {
  const MobileRelease({
    required this.latestVersion,
    required this.latestBuild,
    required this.minimumBuild,
    required this.downloadUrl,
    required this.releaseNotes,
  });

  final String latestVersion;
  final int latestBuild;
  final int minimumBuild;
  final String downloadUrl;
  final String releaseNotes;

  factory MobileRelease.fromJson(Map<String, dynamic> json) => MobileRelease(
    latestVersion: json['latest_version'] as String? ?? '1.0.0',
    latestBuild: json['latest_build'] as int? ?? 1,
    minimumBuild: json['minimum_build'] as int? ?? 1,
    downloadUrl: json['download_url'] as String? ?? '',
    releaseNotes: json['release_notes'] as String? ?? '',
  );
}
