import 'package:flutter_test/flutter_test.dart';
import 'package:synapse_memo/main.dart';

void main() {
  testWidgets('SynapseMemo app launches', (tester) async {
    await tester.pumpWidget(const SynapseMemoApp());
    expect(find.text('SynapseMemo'), findsOneWidget);
  });
}
