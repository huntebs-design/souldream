import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../core/theme.dart';

class DilSeWordmark extends StatelessWidget {
  const DilSeWordmark({super.key, this.height = 42});

  final double height;

  @override
  Widget build(BuildContext context) => SvgPicture.asset(
    'assets/dilse-logo.svg',
    height: height,
    semanticsLabel: 'DilSe',
  );
}

class DilSeMark extends StatelessWidget {
  const DilSeMark({super.key, this.size = 38});

  final double size;

  @override
  Widget build(BuildContext context) => Container(
    width: size,
    height: size,
    padding: EdgeInsets.all(size * .17),
    decoration: BoxDecoration(
      color: DilSeColours.petal,
      borderRadius: BorderRadius.circular(size * .36),
    ),
    child: SvgPicture.asset('assets/dilse-mark.svg'),
  );
}

class PetalBackdrop extends StatelessWidget {
  const PetalBackdrop({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) => Stack(
    fit: StackFit.expand,
    children: [
      const ColoredBox(color: DilSeColours.paper),
      Positioned(
        right: -110,
        top: -90,
        child: Container(
          width: 280,
          height: 280,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(
              colors: [
                DilSeColours.petal.withValues(alpha: .95),
                DilSeColours.petal.withValues(alpha: 0),
              ],
            ),
          ),
        ),
      ),
      Positioned(
        left: -100,
        bottom: -130,
        child: Container(
          width: 290,
          height: 290,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(
              colors: [
                DilSeColours.saffron.withValues(alpha: .12),
                DilSeColours.saffron.withValues(alpha: 0),
              ],
            ),
          ),
        ),
      ),
      child,
    ],
  );
}
