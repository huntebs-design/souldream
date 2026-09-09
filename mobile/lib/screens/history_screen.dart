import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../core/api_client.dart';
import '../core/models.dart';
import '../core/theme.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key, required this.api, required this.onOpen});

  final ApiClient api;
  final ValueChanged<ChatSession> onOpen;

  @override
  State<HistoryScreen> createState() => HistoryScreenState();
}

class HistoryScreenState extends State<HistoryScreen> {
  final _search = TextEditingController();
  List<ChatSession> _sessions = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
    _search.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final sessions = await widget.api.getSessions();
      if (mounted) setState(() => _sessions = sessions);
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> refresh() => _load();

  Future<void> _delete(ChatSession session) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete this conversation?'),
        content: const Text(
          'This removes the conversation from your DilSe history. This cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Keep conversation'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await widget.api.deleteSession(session.sessionId);
      if (mounted) {
        setState(
          () => _sessions.removeWhere(
            (item) => item.sessionId == session.sessionId,
          ),
        );
      }
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final query = _search.text.trim().toLowerCase();
    final visible = query.isEmpty
        ? _sessions
        : _sessions
              .where(
                (session) =>
                    session.preview.toLowerCase().contains(query) ||
                    session.mode.label.toLowerCase().contains(query),
              )
              .toList();
    return Scaffold(
      appBar: AppBar(title: const Text('Conversations')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(18, 8, 18, 14),
              sliver: SliverToBoxAdapter(
                child: TextField(
                  controller: _search,
                  decoration: const InputDecoration(
                    hintText: 'Search your conversations',
                    prefixIcon: Icon(Icons.search_rounded),
                  ),
                ),
              ),
            ),
            if (_loading)
              const SliverFillRemaining(
                hasScrollBody: false,
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_error != null)
              SliverFillRemaining(
                hasScrollBody: false,
                child: _HistoryMessage(
                  icon: Icons.cloud_off_outlined,
                  title: _error!,
                  action: TextButton(
                    onPressed: _load,
                    child: const Text('Try again'),
                  ),
                ),
              )
            else if (visible.isEmpty)
              SliverFillRemaining(
                hasScrollBody: false,
                child: _HistoryMessage(
                  icon: Icons.chat_bubble_outline_rounded,
                  title: query.isEmpty
                      ? 'Your conversations will appear here.'
                      : 'No conversations match that search.',
                ),
              )
            else
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(18, 4, 18, 100),
                sliver: SliverList.separated(
                  itemCount: visible.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 10),
                  itemBuilder: (context, index) {
                    final session = visible[index];
                    return Dismissible(
                      key: ValueKey(session.sessionId),
                      direction: DismissDirection.endToStart,
                      confirmDismiss: (_) async {
                        await _delete(session);
                        return false;
                      },
                      background: Container(
                        alignment: Alignment.centerRight,
                        padding: const EdgeInsets.only(right: 24),
                        decoration: BoxDecoration(
                          color: const Color(0xFF9D2D3F),
                          borderRadius: BorderRadius.circular(22),
                        ),
                        child: const Icon(
                          Icons.delete_outline,
                          color: Colors.white,
                        ),
                      ),
                      child: _SessionTile(
                        session: session,
                        onTap: () => widget.onOpen(session),
                      ),
                    );
                  },
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _SessionTile extends StatelessWidget {
  const _SessionTile({required this.session, required this.onTap});

  final ChatSession session;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final isPartner = session.mode == ChatMode.partner;
    final date = session.lastActivity == null
        ? ''
        : DateFormat('d MMM').format(session.lastActivity!.toLocal());
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(22),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 43,
                height: 43,
                decoration: BoxDecoration(
                  color: isPartner
                      ? DilSeColours.leaf.withValues(alpha: .1)
                      : DilSeColours.petal,
                  borderRadius: BorderRadius.circular(15),
                ),
                child: Icon(
                  isPartner ? Icons.forum_outlined : Icons.favorite_outline,
                  color: isPartner ? DilSeColours.leaf : DilSeColours.mulberry,
                ),
              ),
              const SizedBox(width: 13),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            session.preview.replaceAll('\n', ' '),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontWeight: FontWeight.w700,
                              height: 1.3,
                            ),
                          ),
                        ),
                        if (date.isNotEmpty) ...[
                          const SizedBox(width: 10),
                          Text(
                            date,
                            style: Theme.of(context).textTheme.labelSmall
                                ?.copyWith(color: DilSeColours.muted),
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      '${session.mode.label} · ${session.messageCount} messages',
                      style: Theme.of(context).textTheme.bodySmall
                          ?.copyWith(color: DilSeColours.muted),
                    ),
                  ],
                ),
              ),
              const Padding(
                padding: EdgeInsets.only(top: 11),
                child: Icon(
                  Icons.chevron_right_rounded,
                  color: DilSeColours.muted,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _HistoryMessage extends StatelessWidget {
  const _HistoryMessage({required this.icon, required this.title, this.action});

  final IconData icon;
  final String title;
  final Widget? action;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(36),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 42, color: DilSeColours.raspberry),
          const SizedBox(height: 14),
          Text(title, textAlign: TextAlign.center),
          action ?? const SizedBox.shrink(),
        ],
      ),
    ),
  );
}
