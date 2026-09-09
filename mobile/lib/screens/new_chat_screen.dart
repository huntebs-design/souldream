import 'package:flutter/material.dart';

import '../core/models.dart';
import '../core/theme.dart';
import '../widgets/brand.dart';

class NewChatScreen extends StatelessWidget {
  const NewChatScreen({
    super.key,
    required this.displayName,
    required this.onStart,
  });

  final String displayName;
  final void Function(ChatMode mode, PartnerConfig partner, String? starter)
  onStart;

  @override
  Widget build(BuildContext context) {
    final firstName = displayName.trim().split(' ').first;
    return CustomScrollView(
      slivers: [
        SliverAppBar(
          floating: true,
          title: const DilSeWordmark(height: 34),
          actions: [
            Padding(
              padding: const EdgeInsets.only(right: 16),
              child: CircleAvatar(
                radius: 18,
                backgroundColor: DilSeColours.petal,
                foregroundColor: DilSeColours.mulberry,
                child: Text(
                  firstName.isEmpty ? 'D' : firstName[0].toUpperCase(),
                  style: const TextStyle(fontWeight: FontWeight.w800),
                ),
              ),
            ),
          ],
        ),
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(20, 24, 20, 36),
          sliver: SliverList.list(
            children: [
              Text(
                'What would help right now?',
                style: Theme.of(context).textTheme.headlineLarge,
              ),
              const SizedBox(height: 9),
              Text(
                'Choose a mode first. You can change it when you start another conversation.',
                style: Theme.of(context).textTheme.bodyLarge
                    ?.copyWith(color: DilSeColours.muted),
              ),
              const SizedBox(height: 24),
              _ModeCard(
                icon: Icons.favorite_outline_rounded,
                eyebrow: 'THE LISTENER',
                title: 'Talk it through',
                description: 'Explain what happened. DilSe will help you understand the pattern and find your words.',
                colour: DilSeColours.mulberry,
                onTap: () =>
                    onStart(ChatMode.listener, const PartnerConfig(), null),
              ),
              const SizedBox(height: 14),
              _ModeCard(
                icon: Icons.forum_outlined,
                eyebrow: 'THE PARTNER',
                title: 'Practise the conversation',
                description: 'Describe the person in your first message, then rehearse how the exchange may unfold.',
                colour: DilSeColours.leaf,
                onTap: () =>
                    onStart(ChatMode.partner, const PartnerConfig(), null),
              ),
              const SizedBox(height: 34),
              Row(
                children: [
                  const Expanded(child: Divider()),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    child: Text(
                      'OR START WITH A THOUGHT',
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: DilSeColours.raspberry,
                        letterSpacing: 1.1,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                  const Expanded(child: Divider()),
                ],
              ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 8,
                runSpacing: 9,
                children:
                    [
                          'I need to say something difficult',
                          'I want to understand what changed',
                          'Help me set a family boundary',
                          'I miss feeling close',
                          'I need words for what I want',
                        ]
                        .map(
                          (text) => ActionChip(
                            label: Text(text),
                            backgroundColor: Colors.white.withValues(
                              alpha: .82,
                            ),
                            side: const BorderSide(color: DilSeColours.line),
                            shape: const StadiumBorder(),
                            onPressed: () => onStart(
                              ChatMode.listener,
                              const PartnerConfig(),
                              text,
                            ),
                          ),
                        )
                        .toList(),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ModeCard extends StatelessWidget {
  const _ModeCard({
    required this.icon,
    required this.eyebrow,
    required this.title,
    required this.description,
    required this.colour,
    required this.onTap,
  });

  final IconData icon;
  final String eyebrow;
  final String title;
  final String description;
  final Color colour;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Semantics(
    button: true,
    label: '$title. $description',
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(26),
      child: Ink(
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(
          color: colour,
          borderRadius: BorderRadius.circular(26),
          boxShadow: [
            BoxShadow(
              color: colour.withValues(alpha: .16),
              blurRadius: 24,
              offset: const Offset(0, 12),
            ),
          ],
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 50,
              height: 50,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: .14),
                borderRadius: BorderRadius.circular(17),
              ),
              child: Icon(icon, color: Colors.white, size: 27),
            ),
            const SizedBox(width: 17),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    eyebrow,
                    style: const TextStyle(
                      color: Colors.white70,
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1.2,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Text(
                    title,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 22,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 7),
                  Text(
                    description,
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: .84),
                      height: 1.45,
                    ),
                  ),
                ],
              ),
            ),
            const Padding(
              padding: EdgeInsets.only(top: 13),
              child: Icon(Icons.arrow_forward_rounded, color: Colors.white),
            ),
          ],
        ),
      ),
    ),
  );
}
