import 'package:dilse_app/core/models.dart';
import 'package:dilse_app/core/theme.dart';
import 'package:dilse_app/screens/new_chat_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('new conversation starts with the two prominent mode choices', (
    tester,
  ) async {
    ChatMode? selectedMode;
    PartnerConfig? selectedPartner;
    await tester.pumpWidget(
      MaterialApp(
        theme: buildDilSeTheme(),
        home: Scaffold(
          body: NewChatScreen(
            displayName: 'Jojo',
            onStart: (mode, partner, _) {
              selectedMode = mode;
              selectedPartner = partner;
            },
          ),
        ),
      ),
    );

    expect(find.text('Talk it through'), findsOneWidget);
    expect(find.text('Practise the conversation'), findsOneWidget);

    await tester.tap(find.text('Practise the conversation'));
    await tester.pump();

    expect(selectedMode, ChatMode.partner);
    expect(selectedPartner?.intensity, 'explicit');
  });

  test('chat message parsing keeps replies and voice-note metadata', () {
    final message = ChatMessage.fromJson({
      'id': 14,
      'role': 'assistant',
      'content': 'I hear you.',
      'source': 'admin',
      'created_at': '2026-08-18T12:00:00+00:00',
      'reply_to_message_id': 13,
      'reply_to_content': 'Can we talk?',
      'voice_note_id': 8,
      'voice_note_filename': 'voice-note.wav',
      'voice_note_duration_seconds': 12.5,
    });

    expect(message.isUser, isFalse);
    expect(message.replyToMessageId, 13);
    expect(message.hasVoiceNote, isTrue);
    expect(message.voiceDuration, 12.5);
  });
}
