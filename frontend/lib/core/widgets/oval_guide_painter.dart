import 'package:flutter/material.dart';

class OvalGuidePainter extends CustomPainter {
  final Color borderColor;
  final bool isFaceDetected;

  OvalGuidePainter({required this.borderColor, required this.isFaceDetected});

  @override
  void paint(Canvas canvas, Size size) {
    final double width = size.width;
    final double height = size.height;
    
    // Oval bounds in center of screen
    final double ovalWidth = width * 0.70;
    final double ovalHeight = height * 0.45;
    final Rect ovalRect = Rect.fromCenter(
      center: Offset(width / 2, height * 0.45),
      width: ovalWidth,
      height: ovalHeight,
    );

    // Path representing the screen bounds
    final Path backgroundPath = Path()..addRect(Rect.fromLTWH(0, 0, width, height));
    
    // Path representing the oval cutout
    final Path ovalPath = Path()..addOval(ovalRect);
    
    // Create subtraction (dimmed background with transparent oval hole)
    final Path cutoutPath = Path.combine(
      PathOperation.difference,
      backgroundPath,
      ovalPath,
    );

    final Paint backgroundPaint = Paint()
      ..color = Colors.black.withOpacity(0.65)
      ..style = PaintingStyle.fill;
      
    canvas.drawPath(cutoutPath, backgroundPaint);

    // Draw the oval border
    final Paint borderPaint = Paint()
      ..color = borderColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.5;
      
    canvas.drawOval(ovalRect, borderPaint);
    
    // Draw alignment crosshairs/indicators if face is not detected
    if (!isFaceDetected) {
      final Paint crosshairPaint = Paint()
        ..color = Colors.white24
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.5;
        
      canvas.drawLine(
        Offset(width / 2 - 15, height * 0.45),
        Offset(width / 2 + 15, height * 0.45),
        crosshairPaint,
      );
      canvas.drawLine(
        Offset(width / 2, height * 0.45 - 15),
        Offset(width / 2, height * 0.45 + 15),
        crosshairPaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant OvalGuidePainter oldDelegate) {
    return oldDelegate.borderColor != borderColor || oldDelegate.isFaceDetected != isFaceDetected;
  }
}
