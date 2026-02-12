import 'package:flutter_test/flutter_test.dart';

import 'package:flutter_frontend/main.dart';

void main() {
  testWidgets('RAG v2 landing text renders', (WidgetTester tester) async {
    await tester.pumpWidget(const MyApp());

    expect(find.text('RAG Demo v2'), findsOneWidget);
    expect(find.text('Ask anything about your indexed documents.'), findsOneWidget);
  });
}
