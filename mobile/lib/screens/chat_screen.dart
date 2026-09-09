import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_linkify/flutter_linkify.dart';
import 'package:intl/intl.dart';
import 'package:just_audio/just_audio.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:uuid/uuid.dart';

import '../core/api_client.dart';
import '../core/models.dart';
import '../core/theme.dart';
import '../widgets/brand.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({
    super.key,
    required this.api,
    required this.mode,
    this.existingSession,
    this.initialPartner = const PartnerConfig(),
    this.initialDraft,
  });

  final ApiClient api;
  final ChatMode mode;
  final ChatSession? existingSession;
  final PartnerConfig initialPartner;
  final String? initialDraft;

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _scaffoldKey = GlobalKey<ScaffoldState>();
  final _composer = TextEditingController();
  final _characterDescription = TextEditingController();
  final _scrollController = ScrollController();
  final _recorder = AudioRecorder();

  late final String _sessionId;
  late PartnerConfig _partner;
  List<ChatMessage> _messages = [];
  Catalog _catalog = Catalog.empty;
  ChatMessage? _replyingTo;
  Timer? _pollTimer;
  Timer? _typingTimer;
  Timer? _recordingTimer;
  bool _loading = false;
  bool _sending = false;
  bool _waitingForDilSe = false;
  bool _recording = false;
  bool _sendingVoice = false;
  int _recordingSeconds = 0;
  String? _error;

  @override
  void initState() {
    super.initState();
    _sessionId =
        widget.existingSession?.sessionId ??
        'mobile_${DateTime.now().millisecondsSinceEpoch}_${const Uuid().v4().split('-').first}';
    _partner = widget.existingSession?.partnerConfig ?? widget.initialPartner;
    _characterDescription.text = _partner.characterDescription;
    _composer.text = widget.initialDraft ?? '';
    _loadCatalog();
    if (widget.existingSession != null) _loadMessages();
    _pollTimer = Timer.periodic(const Duration(seconds: 3), (_) => _sync());
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _typingTimer?.cancel();
    _recordingTimer?.cancel();
    unawaited(_recorder.dispose());
    _composer.dispose();
    _characterDescription.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadCatalog() async {
    try {
      final catalog = await widget.api.getCatalog();
      if (mounted) setState(() => _catalog = catalog);
    } catch (_) {}
  }

  Future<void> _loadMessages() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final messages = await widget.api.getMessages(_sessionId);
      if (!mounted) return;
      setState(() {
        _messages = messages;
        _waitingForDilSe = false;
      });
      await _markRead();
      _scrollToLatest(jump: true);
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _sync() async {
    if (_messages.isEmpty || _sending) return;
    final lastId = _messages
        .where((message) => message.id > 0)
        .fold<int>(
          0,
          (latest, message) => message.id > latest ? message.id : latest,
        );
    try {
      final sync = await widget.api.sync(_sessionId, lastId);
      final updates = (sync['updates'] as List<dynamic>? ?? [])
          .map((item) => ChatMessage.fromJson(item as Map<String, dynamic>))
          .where(
            (message) => !_messages.any((current) => current.id == message.id),
          )
          .toList();
      if (updates.isEmpty || !mounted) return;
      setState(() {
        _messages.addAll(updates);
        _waitingForDilSe = false;
      });
      await _markRead();
      _scrollToLatest();
    } catch (_) {}
  }

  Future<void> _markRead() async {
    final ids = _messages
        .where((message) => !message.isUser && message.id > 0)
        .map((message) => message.id)
        .toList();
    try {
      await widget.api.markRead(_sessionId, ids);
    } catch (_) {}
  }

  void _onTyping(String value) {
    if (_messages.isEmpty) return;
    _typingTimer?.cancel();
    unawaited(widget.api.updateTyping(_sessionId, value.trim().isNotEmpty));
    _typingTimer = Timer(const Duration(seconds: 2), () {
      unawaited(widget.api.updateTyping(_sessionId, false));
    });
  }

  Future<void> _send() async {
    final text = _composer.text.trim();
    if (text.isEmpty || _sending || _sendingVoice) return;
    FocusScope.of(context).unfocus();
    _typingTimer?.cancel();
    if (_messages.isNotEmpty) {
      unawaited(widget.api.updateTyping(_sessionId, false));
    }
    final firstPartnerDescription =
        widget.mode == ChatMode.partner &&
        _messages.isEmpty &&
        _partner.characterDescription.trim().isEmpty;
    if (firstPartnerDescription) {
      _partner = _partner.copyWith(characterDescription: text);
      _characterDescription.text = text;
    }
    final optimistic = ChatMessage(
      id: -DateTime.now().millisecondsSinceEpoch,
      role: 'user',
      content: text,
      source: 'user',
      createdAt: DateTime.now(),
      replyToMessageId: _replyingTo?.id,
      replyToContent: _replyingTo?.content,
      pending: true,
    );
    final replyId = _replyingTo?.id;
    _composer.clear();
    setState(() {
      _messages.add(optimistic);
      _replyingTo = null;
      _sending = true;
      _error = null;
    });
    _scrollToLatest();
    final started = DateTime.now();
    try {
      final result = await widget.api.sendMessage(
        sessionId: _sessionId,
        message: text,
        mode: widget.mode,
        partner: _partner,
        replyToMessageId: replyId,
      );
      if (result.delivery == 'ai') {
        final elapsed = DateTime.now().difference(started);
        const minimumVisibleWait = Duration(milliseconds: 2200);
        if (elapsed < minimumVisibleWait) {
          await Future<void>.delayed(minimumVisibleWait - elapsed);
        }
      }
      final messages = await widget.api.getMessages(_sessionId);
      if (!mounted) return;
      setState(() {
        _messages = messages;
        _waitingForDilSe = result.delivery == 'waiting_for_admin';
      });
      await _markRead();
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _messages.remove(optimistic);
        _composer.text = text;
        _error = error.message;
      });
    } finally {
      if (mounted) {
        setState(() => _sending = false);
        _scrollToLatest();
      }
    }
  }

  Future<void> _toggleRecording() async {
    if (_sending || _sendingVoice) return;
    if (_recording) {
      await _finishRecording();
      return;
    }
    final permission = await _recorder.hasPermission();
    if (!permission) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Allow microphone access to record a voice note.'),
          ),
        );
      }
      return;
    }
    final directory = await getTemporaryDirectory();
    final path =
        '${directory.path}/dilse-${DateTime.now().millisecondsSinceEpoch}.wav';
    await _recorder.start(
      const RecordConfig(
        encoder: AudioEncoder.wav,
        sampleRate: 16000,
        numChannels: 1,
        bitRate: 256000,
        autoGain: true,
        echoCancel: true,
        noiseSuppress: true,
      ),
      path: path,
    );
    _recordingTimer?.cancel();
    _recordingTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      setState(() => _recordingSeconds += 1);
      if (_recordingSeconds >= 180) unawaited(_finishRecording());
    });
    setState(() {
      _recording = true;
      _recordingSeconds = 0;
    });
  }

  Future<void> _finishRecording() async {
    _recordingTimer?.cancel();
    final path = await _recorder.stop();
    if (mounted) {
      setState(() {
        _recording = false;
        _sendingVoice = true;
      });
    }
    if (path == null) {
      if (mounted) setState(() => _sendingVoice = false);
      return;
    }
    try {
      final bytes = await File(path).readAsBytes();
      if (bytes.length < 48) {
        throw const ApiException(
          'The voice note was too short. Record it again.',
        );
      }
      await widget.api.sendVoiceNote(
        sessionId: _sessionId,
        audioBytes: bytes,
        uploadId: const Uuid().v4().replaceAll('-', '_'),
        mode: widget.mode,
        partner: _partner,
        replyToMessageId: _replyingTo?.id,
      );
      final messages = await widget.api.getMessages(_sessionId);
      if (mounted) {
        setState(() {
          _messages = messages;
          _replyingTo = null;
          _waitingForDilSe = true;
        });
        _scrollToLatest();
      }
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      try {
        await File(path).delete();
      } catch (_) {}
      if (mounted) setState(() => _sendingVoice = false);
    }
  }

  void _scrollToLatest({bool jump = false}) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;
      final target = _scrollController.position.maxScrollExtent;
      if (jump) {
        _scrollController.jumpTo(target);
      } else {
        _scrollController.animateTo(
          target,
          duration: const Duration(milliseconds: 260),
          curve: Curves.easeOutCubic,
        );
      }
    });
  }

  Future<void> _messageActions(ChatMessage message) async {
    final action = await showModalBottomSheet<String>(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.reply_rounded),
              title: const Text('Reply to this message'),
              onTap: () => Navigator.pop(context, 'reply'),
            ),
            if (!message.isUser)
              ListTile(
                leading: const Icon(Icons.flag_outlined),
                title: const Text('Report a problem with this response'),
                onTap: () => Navigator.pop(context, 'report'),
              ),
          ],
        ),
      ),
    );
    if (!mounted) return;
    if (action == 'reply') {
      setState(() => _replyingTo = message);
      FocusScope.of(context).requestFocus(FocusNode());
    } else if (action == 'report') {
      await _reportResponse(message);
    }
  }

  Future<void> _reportResponse(ChatMessage message) async {
    const categories = {
      'too_conclusive': 'Reached a conclusion too quickly',
      'wrong_language': 'Used the wrong language or vocabulary',
      'wrong_tone': 'The tone did not fit',
      'wrong_facts': 'Changed or invented a fact',
      'too_long': 'The response was too long',
      'not_my_voice': 'The suggested words did not sound like me',
    };
    final selected = await showDialog<String>(
      context: context,
      builder: (context) => SimpleDialog(
        title: const Text('What should DilSe improve?'),
        children: categories.entries
            .map(
              (entry) => SimpleDialogOption(
                onPressed: () => Navigator.pop(context, entry.key),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 7),
                  child: Text(entry.value),
                ),
              ),
            )
            .toList(),
      ),
    );
    if (selected == null) return;
    try {
      await widget.api.reportMessage(message.id, selected);
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text('Feedback recorded.')));
      }
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    key: _scaffoldKey,
    endDrawer: _SettingsDrawer(
      mode: widget.mode,
      api: widget.api,
      sessionId: _sessionId,
      catalog: _catalog,
      partner: _partner,
      descriptionController: _characterDescription,
      onSave: (partner) {
        setState(() => _partner = partner);
        Navigator.pop(context);
      },
    ),
    appBar: AppBar(
      titleSpacing: 4,
      title: Row(
        children: [
          const DilSeMark(size: 38),
          const SizedBox(width: 10),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'DilSe',
                style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800),
              ),
              Text(
                widget.mode == ChatMode.listener
                    ? 'LISTENER MODE'
                    : 'PARTNER MODE · ${_partner.intensity.toUpperCase()}',
                style: const TextStyle(
                  color: DilSeColours.raspberry,
                  fontSize: 9.5,
                  fontWeight: FontWeight.w800,
                  letterSpacing: .8,
                ),
              ),
            ],
          ),
        ],
      ),
      actions: [
        IconButton(
          tooltip: 'Conversation settings',
          onPressed: () => _scaffoldKey.currentState?.openEndDrawer(),
          icon: const Icon(Icons.tune_rounded),
        ),
        const SizedBox(width: 6),
      ],
    ),
    body: Column(
      children: [
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _buildConversation(),
        ),
        if (_error != null)
          Container(
            width: double.infinity,
            color: const Color(0xFFFFECEC),
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 9),
            child: Text(
              _error!,
              style: const TextStyle(color: Color(0xFF9D2D3F), fontSize: 13),
            ),
          ),
        _buildComposer(),
      ],
    ),
  );

  Widget _buildConversation() {
    if (_messages.isEmpty && !_sending) {
      return _EmptyConversation(mode: widget.mode);
    }
    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.fromLTRB(14, 18, 14, 22),
      itemCount: _messages.length + ((_sending || _waitingForDilSe) ? 1 : 0),
      itemBuilder: (context, index) {
        if (index == _messages.length) {
          return _TypingBubble(waiting: _waitingForDilSe && !_sending);
        }
        final message = _messages[index];
        return _MessageBubble(
          key: ValueKey(message.id),
          message: message,
          api: widget.api,
          onLongPress: () => _messageActions(message),
        );
      },
    );
  }

  Widget _buildComposer() => SafeArea(
    top: false,
    child: Container(
      padding: const EdgeInsets.fromLTRB(12, 9, 12, 11),
      decoration: const BoxDecoration(
        color: DilSeColours.paper,
        border: Border(top: BorderSide(color: DilSeColours.line)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (_replyingTo != null)
            Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.fromLTRB(12, 8, 6, 8),
              decoration: BoxDecoration(
                color: DilSeColours.petal,
                borderRadius: BorderRadius.circular(13),
              ),
              child: Row(
                children: [
                  const Icon(Icons.reply_rounded, size: 18),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _replyingTo!.content,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 12.5),
                    ),
                  ),
                  IconButton(
                    visualDensity: VisualDensity.compact,
                    onPressed: () => setState(() => _replyingTo = null),
                    icon: const Icon(Icons.close_rounded, size: 18),
                  ),
                ],
              ),
            ),
          if (_recording)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const _RecordingDot(),
                  const SizedBox(width: 8),
                  Text(
                    'Recording ${_formatDuration(_recordingSeconds)} · tap stop to send',
                    style: const TextStyle(
                      color: DilSeColours.raspberry,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              IconButton.filledTonal(
                tooltip: _recording
                    ? 'Stop and send voice note'
                    : 'Record voice note',
                onPressed: _toggleRecording,
                style: IconButton.styleFrom(
                  backgroundColor: _recording
                      ? const Color(0xFFFFDDE2)
                      : DilSeColours.petal,
                  foregroundColor: _recording
                      ? const Color(0xFF9D2D3F)
                      : DilSeColours.mulberry,
                ),
                icon: _sendingVoice
                    ? const SizedBox.square(
                        dimension: 19,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Icon(
                        _recording
                            ? Icons.stop_rounded
                            : Icons.mic_none_rounded,
                      ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: TextField(
                  controller: _composer,
                  onChanged: _onTyping,
                  minLines: 1,
                  maxLines: 6,
                  textCapitalization: TextCapitalization.sentences,
                  keyboardType: TextInputType.multiline,
                  decoration: InputDecoration(
                    hintText:
                        widget.mode == ChatMode.partner && _messages.isEmpty
                        ? 'Describe this person and how they usually respond…'
                        : 'Message DilSe…',
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 13,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              IconButton.filled(
                tooltip: 'Send message',
                onPressed: _sending || _sendingVoice ? null : _send,
                style: IconButton.styleFrom(
                  backgroundColor: DilSeColours.mulberry,
                  foregroundColor: Colors.white,
                  disabledBackgroundColor: DilSeColours.line,
                ),
                icon: const Icon(Icons.arrow_upward_rounded),
              ),
            ],
          ),
        ],
      ),
    ),
  );

  static String _formatDuration(int seconds) =>
      '${(seconds ~/ 60).toString().padLeft(2, '0')}:${(seconds % 60).toString().padLeft(2, '0')}';
}

class _EmptyConversation extends StatelessWidget {
  const _EmptyConversation({required this.mode});

  final ChatMode mode;

  @override
  Widget build(BuildContext context) => Center(
    child: SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(28, 28, 28, 90),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const DilSeMark(size: 68),
          const SizedBox(height: 22),
          Text(
            mode == ChatMode.listener
                ? 'Start wherever it feels easiest.'
                : 'Who should DilSe become?',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 12),
          Text(
            mode == ChatMode.listener
                ? 'Share one moment, feeling or conversation. DilSe will follow your concern and ask one focused question at a time.'
                : 'In your first message, describe the person, their personality and how they usually respond. DilSe will remember that description for this conversation.',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodyLarge
                ?.copyWith(color: DilSeColours.muted),
          ),
          if (mode == ChatMode.partner) ...[
            const SizedBox(height: 18),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: DilSeColours.leaf.withValues(alpha: .08),
                borderRadius: BorderRadius.circular(18),
              ),
              child: const Text(
                'Example: “Be my husband. He cares through practical things, avoids emotional conversations and becomes defensive when family is mentioned.”',
                textAlign: TextAlign.left,
                style: TextStyle(height: 1.45),
              ),
            ),
          ],
        ],
      ),
    ),
  );
}

class _TypingBubble extends StatelessWidget {
  const _TypingBubble({required this.waiting});

  final bool waiting;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        const DilSeMark(size: 31),
        const SizedBox(width: 7),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
          decoration: const BoxDecoration(
            color: DilSeColours.petal,
            borderRadius: BorderRadius.only(
              topLeft: Radius.circular(17),
              topRight: Radius.circular(17),
              bottomRight: Radius.circular(17),
              bottomLeft: Radius.circular(5),
            ),
          ),
          child: waiting
              ? const Text(
                  'DilSe is preparing a response…',
                  style: TextStyle(fontSize: 12.5, color: DilSeColours.muted),
                )
              : const _ThreeDots(),
        ),
      ],
    ),
  );
}

class _ThreeDots extends StatelessWidget {
  const _ThreeDots();

  @override
  Widget build(BuildContext context) => const Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      _Dot(),
      SizedBox(width: 4),
      _Dot(opacity: .7),
      SizedBox(width: 4),
      _Dot(opacity: .4),
    ],
  );
}

class _Dot extends StatelessWidget {
  const _Dot({this.opacity = 1});

  final double opacity;

  @override
  Widget build(BuildContext context) => Container(
    width: 6,
    height: 6,
    decoration: BoxDecoration(
      color: DilSeColours.raspberry.withValues(alpha: opacity),
      shape: BoxShape.circle,
    ),
  );
}

class _RecordingDot extends StatelessWidget {
  const _RecordingDot();

  @override
  Widget build(BuildContext context) => Container(
    width: 9,
    height: 9,
    decoration: const BoxDecoration(
      color: Color(0xFFC5334E),
      shape: BoxShape.circle,
    ),
  );
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({
    super.key,
    required this.message,
    required this.api,
    required this.onLongPress,
  });

  final ChatMessage message;
  final ApiClient api;
  final VoidCallback onLongPress;

  @override
  Widget build(BuildContext context) {
    final isUser = message.isUser;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        mainAxisAlignment: isUser
            ? MainAxisAlignment.end
            : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (!isUser) ...[const DilSeMark(size: 31), const SizedBox(width: 7)],
          Flexible(
            child: GestureDetector(
              onLongPress: onLongPress,
              child: Container(
                constraints: const BoxConstraints(maxWidth: 560),
                padding: const EdgeInsets.fromLTRB(13, 10, 13, 8),
                decoration: BoxDecoration(
                  color: isUser ? DilSeColours.mulberry : DilSeColours.petal,
                  borderRadius: BorderRadius.only(
                    topLeft: const Radius.circular(18),
                    topRight: const Radius.circular(18),
                    bottomLeft: Radius.circular(isUser ? 18 : 5),
                    bottomRight: Radius.circular(isUser ? 5 : 18),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (message.replyToContent != null)
                      Container(
                        width: double.infinity,
                        margin: const EdgeInsets.only(bottom: 7),
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: (isUser ? Colors.white : DilSeColours.mulberry)
                              .withValues(alpha: .12),
                          borderRadius: BorderRadius.circular(9),
                        ),
                        child: Text(
                          message.replyToContent!,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: isUser ? Colors.white70 : DilSeColours.muted,
                            fontSize: 11.5,
                          ),
                        ),
                      ),
                    if (message.hasAttachment)
                      ClipRRect(
                        borderRadius: BorderRadius.circular(13),
                        child: Image.network(
                          api.attachmentUrl(message.id),
                          headers: api.mediaHeaders,
                          fit: BoxFit.cover,
                          errorBuilder: (_, _, _) => const Padding(
                            padding: EdgeInsets.all(14),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(Icons.broken_image_outlined),
                                SizedBox(width: 8),
                                Text('Image unavailable'),
                              ],
                            ),
                          ),
                        ),
                      ),
                    if (message.hasVoiceNote)
                      _VoiceNotePlayer(
                        api: api,
                        messageId: message.id,
                        duration: message.voiceDuration,
                        isUser: isUser,
                      ),
                    if (message.content.isNotEmpty &&
                        message.content != 'Voice note') ...[
                      if (message.hasAttachment || message.hasVoiceNote)
                        const SizedBox(height: 8),
                      Linkify(
                        text: message.content,
                        onOpen: (link) => launchUrl(
                          Uri.parse(link.url),
                          mode: LaunchMode.externalApplication,
                        ),
                        style: TextStyle(
                          color: isUser ? Colors.white : DilSeColours.ink,
                          fontSize: 15.5,
                          height: 1.48,
                        ),
                        linkStyle: TextStyle(
                          color: isUser ? Colors.white : DilSeColours.raspberry,
                          decoration: TextDecoration.underline,
                          decorationColor: isUser
                              ? Colors.white70
                              : DilSeColours.raspberry,
                        ),
                      ),
                    ],
                    const SizedBox(height: 4),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          message.createdAt == null
                              ? ''
                              : DateFormat('h:mm a')
                                    .format(message.createdAt!.toLocal()),
                          style: TextStyle(
                            color: isUser ? Colors.white60 : DilSeColours.muted,
                            fontSize: 9.5,
                          ),
                        ),
                        if (message.pending) ...[
                          const SizedBox(width: 5),
                          Icon(
                            Icons.schedule_rounded,
                            size: 11,
                            color: isUser ? Colors.white60 : DilSeColours.muted,
                          ),
                        ],
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
          if (isUser) const SizedBox(width: 3),
        ],
      ),
    );
  }
}

class _VoiceNotePlayer extends StatefulWidget {
  const _VoiceNotePlayer({
    required this.api,
    required this.messageId,
    required this.duration,
    required this.isUser,
  });

  final ApiClient api;
  final int messageId;
  final double? duration;
  final bool isUser;

  @override
  State<_VoiceNotePlayer> createState() => _VoiceNotePlayerState();
}

class _VoiceNotePlayerState extends State<_VoiceNotePlayer> {
  final _player = AudioPlayer();
  bool _loading = false;
  bool _loaded = false;
  String? _path;

  @override
  void dispose() {
    unawaited(_player.dispose());
    final path = _path;
    if (path != null) unawaited(_removeTemporaryFile(path));
    super.dispose();
  }

  Future<void> _removeTemporaryFile(String path) async {
    try {
      await File(path).delete();
    } on FileSystemException {
      // Android may still hold the temporary audio file while the player closes.
    }
  }

  Future<void> _toggle() async {
    if (_loading) return;
    if (_player.playing) {
      await _player.pause();
      return;
    }
    try {
      if (!_loaded) {
        setState(() => _loading = true);
        final Uint8List bytes = await widget.api.getVoiceNote(widget.messageId);
        final directory = await getTemporaryDirectory();
        _path = '${directory.path}/dilse-play-${widget.messageId}.wav';
        await File(_path!).writeAsBytes(bytes, flush: true);
        await _player.setFilePath(_path!);
        _loaded = true;
      }
      if (_player.processingState == ProcessingState.completed) {
        await _player.seek(Duration.zero);
      }
      await _player.play();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('The voice note could not be played.')),
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final foreground = widget.isUser ? Colors.white : DilSeColours.mulberry;
    return StreamBuilder<PlayerState>(
      stream: _player.playerStateStream,
      builder: (context, snapshot) {
        final playing = snapshot.data?.playing ?? false;
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            IconButton(
              visualDensity: VisualDensity.compact,
              onPressed: _toggle,
              color: foreground,
              icon: _loading
                  ? SizedBox.square(
                      dimension: 19,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: foreground,
                      ),
                    )
                  : Icon(
                      playing ? Icons.pause_rounded : Icons.play_arrow_rounded,
                    ),
            ),
            SizedBox(
              width: 92,
              child: LinearProgressIndicator(
                value: playing ? null : 0,
                minHeight: 3,
                color: foreground,
                backgroundColor: foreground.withValues(alpha: .2),
              ),
            ),
            const SizedBox(width: 8),
            Text(
              _formatSeconds(widget.duration?.round() ?? 0),
              style: TextStyle(color: foreground, fontSize: 11),
            ),
          ],
        );
      },
    );
  }

  static String _formatSeconds(int seconds) =>
      '${seconds ~/ 60}:${(seconds % 60).toString().padLeft(2, '0')}';
}

class _SettingsDrawer extends StatefulWidget {
  const _SettingsDrawer({
    required this.mode,
    required this.api,
    required this.sessionId,
    required this.catalog,
    required this.partner,
    required this.descriptionController,
    required this.onSave,
  });

  final ChatMode mode;
  final ApiClient api;
  final String sessionId;
  final Catalog catalog;
  final PartnerConfig partner;
  final TextEditingController descriptionController;
  final ValueChanged<PartnerConfig> onSave;

  @override
  State<_SettingsDrawer> createState() => _SettingsDrawerState();
}

class _SettingsDrawerState extends State<_SettingsDrawer> {
  late String? scenario = widget.partner.scenario;
  late String? persona = widget.partner.persona;
  late String intensity = widget.partner.intensity;
  late String difficulty = widget.partner.difficulty;

  int get wordCount => widget.descriptionController.text
      .trim()
      .split(RegExp(r'\s+'))
      .where((word) => word.isNotEmpty)
      .length;

  @override
  Widget build(BuildContext context) => Drawer(
    width: MediaQuery.sizeOf(context).width * .92,
    backgroundColor: DilSeColours.paper,
    child: SafeArea(
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 30),
        children: [
          Row(
            children: [
              Text(
                'Conversation settings',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const Spacer(),
              IconButton(
                onPressed: () => Navigator.pop(context),
                icon: const Icon(Icons.close_rounded),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: widget.mode == ChatMode.listener
                  ? DilSeColours.petal
                  : DilSeColours.leaf.withValues(alpha: .08),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Row(
              children: [
                Icon(
                  widget.mode == ChatMode.listener
                      ? Icons.favorite_outline
                      : Icons.forum_outlined,
                  color: widget.mode == ChatMode.listener
                      ? DilSeColours.mulberry
                      : DilSeColours.leaf,
                ),
                const SizedBox(width: 11),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${widget.mode.label} mode',
                        style: const TextStyle(fontWeight: FontWeight.w800),
                      ),
                      Text(
                        widget.mode == ChatMode.listener
                            ? 'Reflection, perspective and practical words.'
                            : 'In-character conversation practice.',
                        style: const TextStyle(
                          color: DilSeColours.muted,
                          fontSize: 12.5,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          if (widget.mode == ChatMode.partner) ...[
            const _DrawerLabel('CHARACTER'),
            DropdownButtonFormField<String>(
              initialValue: persona,
              decoration: const InputDecoration(
                labelText: 'Who are you practising with?',
              ),
              items: widget.catalog.personas
                  .map(
                    (item) => DropdownMenuItem(
                      value: item.slug,
                      child: Text(item.name),
                    ),
                  )
                  .toList(),
              onChanged: (value) => setState(() => persona = value),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: scenario,
              decoration: const InputDecoration(labelText: 'Conversation'),
              items: widget.catalog.scenarios
                  .map(
                    (item) => DropdownMenuItem(
                      value: item.slug,
                      child: Text(item.name),
                    ),
                  )
                  .toList(),
              onChanged: (value) => setState(() => scenario = value),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: widget.descriptionController,
              minLines: 4,
              maxLines: 9,
              maxLength: 75000,
              onChanged: (_) => setState(() {}),
              decoration: InputDecoration(
                labelText: 'Describe this person',
                alignLabelWithHint: true,
                helperText:
                    '$wordCount of 5,000 words · personality, habits and usual reactions',
                counterText: '',
                errorText: wordCount > 5000
                    ? 'Shorten this description to 5,000 words.'
                    : null,
              ),
            ),
            const _DrawerLabel('ROLEPLAY'),
            DropdownButtonFormField<String>(
              initialValue: difficulty,
              decoration: const InputDecoration(
                labelText: 'How should they respond?',
              ),
              items:
                  const {
                        'supportive': 'Supportive',
                        'realistic': 'Realistic',
                        'resistant': 'Resistant',
                      }.entries
                      .map(
                        (entry) => DropdownMenuItem(
                          value: entry.key,
                          child: Text(entry.value),
                        ),
                      )
                      .toList(),
              onChanged: (value) =>
                  setState(() => difficulty = value ?? difficulty),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: intensity,
              decoration: const InputDecoration(labelText: 'Intimacy detail'),
              items:
                  const {
                        'explicit': 'Explicit',
                        'direct': 'Direct',
                        'romantic': 'Romantic',
                      }.entries
                      .map(
                        (entry) => DropdownMenuItem(
                          value: entry.key,
                          child: Text(entry.value),
                        ),
                      )
                      .toList(),
              onChanged: (value) =>
                  setState(() => intensity = value ?? intensity),
            ),
            const SizedBox(height: 18),
            FilledButton(
              onPressed: wordCount > 5000
                  ? null
                  : () => widget.onSave(
                      PartnerConfig(
                        scenario: scenario,
                        persona: persona,
                        intensity: intensity,
                        difficulty: difficulty,
                        characterDescription: widget.descriptionController.text
                            .trim(),
                      ),
                    ),
              child: const Text('Save conversation settings'),
            ),
          ],
          const _DrawerLabel('MEMORY'),
          _ConversationMemory(api: widget.api, sessionId: widget.sessionId),
        ],
      ),
    ),
  );
}

class _DrawerLabel extends StatelessWidget {
  const _DrawerLabel(this.label);

  final String label;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(4, 25, 4, 8),
    child: Text(
      label,
      style: Theme.of(context).textTheme.labelSmall?.copyWith(
        color: DilSeColours.raspberry,
        fontWeight: FontWeight.w800,
        letterSpacing: 1.1,
      ),
    ),
  );
}

class _ConversationMemory extends StatefulWidget {
  const _ConversationMemory({required this.api, required this.sessionId});

  final ApiClient api;
  final String sessionId;

  @override
  State<_ConversationMemory> createState() => _ConversationMemoryState();
}

class _ConversationMemoryState extends State<_ConversationMemory> {
  bool open = false;
  Map<String, dynamic>? memory;
  bool loading = false;

  Future<void> _load() async {
    if (open) {
      setState(() => open = false);
      return;
    }
    setState(() {
      open = true;
      loading = true;
    });
    try {
      memory = await widget.api.getConversationState(widget.sessionId);
    } catch (_) {}
    if (mounted) setState(() => loading = false);
  }

  Future<void> _edit() async {
    final controller = TextEditingController(
      text: memory?['summary'] as String? ?? '',
    );
    final updated = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('What should DilSe remember?'),
        content: TextField(
          controller: controller,
          minLines: 5,
          maxLines: 10,
          maxLength: 1500,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text.trim()),
            child: const Text('Save memory'),
          ),
        ],
      ),
    );
    controller.dispose();
    if (updated == null || updated.isEmpty) return;
    await widget.api.confirmConversationState(widget.sessionId, updated);
    if (mounted) setState(() => memory = {...?memory, 'summary': updated});
  }

  @override
  Widget build(BuildContext context) => Container(
    decoration: BoxDecoration(
      color: Colors.white.withValues(alpha: .75),
      borderRadius: BorderRadius.circular(18),
      border: Border.all(color: DilSeColours.line),
    ),
    child: Column(
      children: [
        ListTile(
          title: const Text('Review what DilSe remembers'),
          trailing: Icon(open ? Icons.expand_less : Icons.expand_more),
          onTap: _load,
        ),
        if (open)
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            child: loading
                ? const LinearProgressIndicator()
                : memory == null
                ? const Text(
                    'DilSe will build a short memory after the conversation begins.',
                    style: TextStyle(color: DilSeColours.muted),
                  )
                : Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        memory!['summary'] as String? ?? '',
                        style: const TextStyle(height: 1.45),
                      ),
                      const SizedBox(height: 8),
                      TextButton.icon(
                        onPressed: _edit,
                        icon: const Icon(Icons.edit_outlined, size: 17),
                        label: const Text('Edit memory'),
                      ),
                    ],
                  ),
          ),
      ],
    ),
  );
}
