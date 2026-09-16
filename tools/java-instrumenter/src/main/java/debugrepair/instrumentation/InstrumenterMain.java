package debugrepair.instrumentation;

import com.github.javaparser.ParserConfiguration;
import com.github.javaparser.StaticJavaParser;
import com.github.javaparser.ast.CompilationUnit;
import com.github.javaparser.ast.Node;
import com.github.javaparser.ast.NodeList;
import com.github.javaparser.ast.body.BodyDeclaration;
import com.github.javaparser.ast.body.ConstructorDeclaration;
import com.github.javaparser.ast.body.MethodDeclaration;
import com.github.javaparser.ast.body.VariableDeclarator;
import com.github.javaparser.ast.expr.AssignExpr;
import com.github.javaparser.ast.expr.BinaryExpr;
import com.github.javaparser.ast.expr.BooleanLiteralExpr;
import com.github.javaparser.ast.expr.EnclosedExpr;
import com.github.javaparser.ast.expr.Expression;
import com.github.javaparser.ast.expr.FieldAccessExpr;
import com.github.javaparser.ast.expr.MethodCallExpr;
import com.github.javaparser.ast.expr.NameExpr;
import com.github.javaparser.ast.expr.SimpleName;
import com.github.javaparser.ast.expr.StringLiteralExpr;
import com.github.javaparser.ast.expr.UnaryExpr;
import com.github.javaparser.ast.expr.VariableDeclarationExpr;
import com.github.javaparser.ast.stmt.BlockStmt;
import com.github.javaparser.ast.stmt.BreakStmt;
import com.github.javaparser.ast.stmt.CatchClause;
import com.github.javaparser.ast.stmt.DoStmt;
import com.github.javaparser.ast.stmt.EmptyStmt;
import com.github.javaparser.ast.stmt.ExpressionStmt;
import com.github.javaparser.ast.stmt.ForEachStmt;
import com.github.javaparser.ast.stmt.ForStmt;
import com.github.javaparser.ast.stmt.IfStmt;
import com.github.javaparser.ast.stmt.LabeledStmt;
import com.github.javaparser.ast.stmt.ReturnStmt;
import com.github.javaparser.ast.stmt.Statement;
import com.github.javaparser.ast.stmt.SwitchEntry;
import com.github.javaparser.ast.stmt.SwitchStmt;
import com.github.javaparser.ast.stmt.SynchronizedStmt;
import com.github.javaparser.ast.stmt.ThrowStmt;
import com.github.javaparser.ast.stmt.TryStmt;
import com.github.javaparser.ast.stmt.WhileStmt;
import com.github.javaparser.ast.type.PrimitiveType;
import com.github.javaparser.ast.type.Type;
import com.github.javaparser.printer.lexicalpreservation.LexicalPreservingPrinter;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Base64;
import java.util.HashSet;
import java.util.List;
import java.util.Set;


public final class InstrumenterMain {
    private InstrumenterMain() {
    }

    public static void main(String[] args) {
        PrintWriter stdout = new PrintWriter(
                new OutputStreamWriter(System.out, StandardCharsets.UTF_8), true);
        PrintWriter stderr = new PrintWriter(
                new OutputStreamWriter(System.err, StandardCharsets.UTF_8), true);
        try {
            String source = readUtf8(System.in);
            if (args.length == 1 && "--normalize".equals(args[0])) {
                stdout.print(normalize(source));
            } else if (args.length == 3 && "--replace-method".equals(args[0])) {
                stdout.print(replaceMethod(source, args[1], args[2]));
            } else if (args.length == 2) {
                stdout.print(instrument(source, args[0], args[1]));
            } else {
                stderr.println(
                        "Expected --normalize, --replace-method, or marker arguments.");
                System.exit(2);
            }
            stdout.flush();
        } catch (Exception exc) {
            stderr.println(exc.getClass().getSimpleName() + ": " + exc.getMessage());
            exc.printStackTrace(stderr);
            System.exit(2);
        }
    }

    static String normalize(String source) {
        configureParser();
        BodyDeclaration<?> member = StaticJavaParser.parseBodyDeclaration(source);

        List<ExpressionStmt> printStatements = new ArrayList<ExpressionStmt>(
                member.findAll(ExpressionStmt.class,
                        InstrumenterMain::isInstrumentationPrintln));
        for (ExpressionStmt statement : printStatements) {
            Node parent = statement.getParentNode().orElse(null);
            if (parent instanceof BlockStmt || parent instanceof SwitchEntry) {
                statement.remove();
            } else {
                statement.replace(new EmptyStmt());
            }
        }

        member.getAllContainedComments().forEach(comment -> comment.remove());
        member.walk(node -> {
            node.removeComment();
            new ArrayList<>(node.getOrphanComments())
                    .forEach(node::removeOrphanComment);
        });

        String normalized = member.toString();
        StaticJavaParser.parseBodyDeclaration(normalized);
        return normalized;
    }

    static String replaceMethod(
            String encodedPayload, String methodName, String prependedMessage) {
        configureParser();
        String[] payload = encodedPayload.trim().split("\\R", -1);
        if (payload.length != 2) {
            throw new IllegalArgumentException(
                    "Method replacement payload must contain two Base64 lines.");
        }

        Base64.Decoder decoder = Base64.getDecoder();
        String compilationUnitSource = new String(
                decoder.decode(payload[0]), StandardCharsets.UTF_8);
        String replacementSource = new String(
                decoder.decode(payload[1]), StandardCharsets.UTF_8);

        CompilationUnit compilationUnit = StaticJavaParser.parse(compilationUnitSource);
        BodyDeclaration<?> replacement = StaticJavaParser.parseBodyDeclaration(
                replacementSource);
        if (!(replacement instanceof MethodDeclaration)) {
            throw new IllegalArgumentException("Replacement must be a method declaration.");
        }
        MethodDeclaration replacementMethod = (MethodDeclaration) replacement;
        if (!methodName.equals(replacementMethod.getNameAsString())) {
            throw new IllegalArgumentException(
                    "Replacement method name does not match " + methodName + ".");
        }
        if (!replacementMethod.getBody().isPresent()) {
            throw new IllegalArgumentException("Replacement method has no body.");
        }

        List<MethodDeclaration> matches = new ArrayList<MethodDeclaration>();
        for (MethodDeclaration method : compilationUnit.findAll(MethodDeclaration.class)) {
            if (methodName.equals(method.getNameAsString())) {
                matches.add(method);
            }
        }
        if (matches.size() != 1) {
            throw new IllegalArgumentException(
                    "Expected one method named " + methodName + ", found " + matches.size());
        }

        LexicalPreservingPrinter.setup(compilationUnit);
        replacementMethod.getBody().get().addStatement(
                0, printStatement(prependedMessage));
        matches.get(0).replace(replacementMethod);

        String printed = LexicalPreservingPrinter.print(compilationUnit);
        StaticJavaParser.parse(printed);
        return printed;
    }

    private static Statement printStatement(String message) {
        FieldAccessExpr systemOut = new FieldAccessExpr(
                new NameExpr("System"), "out");
        MethodCallExpr println = new MethodCallExpr(systemOut, "println");
        println.addArgument(new StringLiteralExpr().setString(message));
        return new ExpressionStmt(println);
    }

    private static boolean isInstrumentationPrintln(ExpressionStmt statement) {
        if (!statement.getExpression().isMethodCallExpr()) {
            return false;
        }
        MethodCallExpr call = statement.getExpression().asMethodCallExpr();
        if (!"println".equals(call.getNameAsString()) || !call.getScope().isPresent()
                || !call.getScope().get().isFieldAccessExpr()
                || call.getArguments().size() != 1) {
            return false;
        }
        FieldAccessExpr out = call.getScope().get().asFieldAccessExpr();
        if (!"out".equals(out.getNameAsString())
                || !out.getScope().isNameExpr()
                || !"System".equals(out.getScope().asNameExpr().getNameAsString())) {
            return false;
        }

        Expression prefix = call.getArgument(0);
        while (prefix.isEnclosedExpr()) {
            prefix = prefix.asEnclosedExpr().getInner();
        }
        while (prefix.isBinaryExpr()
                && prefix.asBinaryExpr().getOperator() == BinaryExpr.Operator.PLUS) {
            prefix = prefix.asBinaryExpr().getLeft();
            while (prefix.isEnclosedExpr()) {
                prefix = prefix.asEnclosedExpr().getInner();
            }
        }
        if (!prefix.isStringLiteralExpr()) {
            return false;
        }
        String message = prefix.asStringLiteralExpr().asString();
        return message.startsWith("// DEBUG")
                || message.startsWith("// START_DEBUG")
                || message.startsWith("// END_DEBUG");
    }

    private static void configureParser() {
        ParserConfiguration configuration = new ParserConfiguration()
                .setLanguageLevel(ParserConfiguration.LanguageLevel.BLEEDING_EDGE);
        StaticJavaParser.setConfiguration(configuration);
    }

    static String instrument(String source, String startMarker, String endMarker) {
        configureParser();

        BodyDeclaration<?> member = StaticJavaParser.parseBodyDeclaration(source);
        BlockStmt body = callableBody(member);
        Type returnType = callableReturnType(member);
        LexicalPreservingPrinter.setup(member);

        RuleInstrumenter instrumenter = new RuleInstrumenter(
                member, startMarker, endMarker, returnType);
        instrumenter.instrument(body, member instanceof ConstructorDeclaration);

        String printed = LexicalPreservingPrinter.print(member);
        try {
            StaticJavaParser.parseBodyDeclaration(printed);
        } catch (RuntimeException exc) {
            throw new IllegalStateException(
                    "Generated source failed reparse:\n" + printed, exc);
        }
        return printed;
    }

    private static BlockStmt callableBody(BodyDeclaration<?> member) {
        if (member instanceof MethodDeclaration) {
            MethodDeclaration method = (MethodDeclaration) member;
            if (!method.getBody().isPresent()) {
                throw new IllegalArgumentException("Method has no body.");
            }
            return method.getBody().get();
        }
        if (member instanceof ConstructorDeclaration) {
            return ((ConstructorDeclaration) member).getBody();
        }
        throw new IllegalArgumentException("Expected a method or constructor declaration.");
    }

    private static Type callableReturnType(BodyDeclaration<?> member) {
        if (member instanceof MethodDeclaration) {
            return ((MethodDeclaration) member).getType().clone();
        }
        return StaticJavaParser.parseType("void");
    }

    private static String readUtf8(InputStream input) throws Exception {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192];
        int read;
        while ((read = input.read(buffer)) != -1) {
            output.write(buffer, 0, read);
        }
        return new String(output.toByteArray(), StandardCharsets.UTF_8);
    }


    private static final class RuleInstrumenter {
        private final String startMarker;
        private final String endMarker;
        private final Type returnType;
        private final Set<String> usedNames = new HashSet<String>();
        private int temporaryCounter;

        RuleInstrumenter(
                BodyDeclaration<?> member,
                String startMarker,
                String endMarker,
                Type returnType) {
            this.startMarker = startMarker;
            this.endMarker = endMarker;
            this.returnType = returnType;
            for (SimpleName name : member.findAll(SimpleName.class)) {
                usedNames.add(name.asString());
            }
        }

        void instrument(BlockStmt body, boolean constructor) {
            processBlock(body);
            int startIndex = 0;
            if (constructor && !body.getStatements().isEmpty()
                    && body.getStatement(0).isExplicitConstructorInvocationStmt()) {
                startIndex = 1;
            }
            body.addStatement(startIndex, printStatement(startMarker));
            if (canCompleteNormally(body)) {
                body.addStatement(printStatement(endMarker));
            }
        }

        private void processBlock(BlockStmt block) {
            processStatementList(block.getStatements());
        }

        private void processStatementList(NodeList<Statement> statements) {
            int index = 0;
            while (index < statements.size()) {
                Statement original = statements.get(index);
                NodeList<Statement> transformed = transform(original);
                int originalPosition = identityIndexOf(transformed, original);

                if (originalPosition >= 0) {
                    for (int offset = 0; offset < originalPosition; offset++) {
                        statements.add(index + offset, transformed.get(offset));
                    }
                    int currentOriginalIndex = index + originalPosition;
                    for (int offset = originalPosition + 1;
                            offset < transformed.size();
                            offset++) {
                        statements.add(
                                currentOriginalIndex + offset - originalPosition,
                                transformed.get(offset));
                    }
                } else {
                    statements.set(index, transformed.get(0));
                    for (int offset = 1; offset < transformed.size(); offset++) {
                        statements.add(index + offset, transformed.get(offset));
                    }
                }
                index += transformed.size();
            }
        }

        private int identityIndexOf(
                NodeList<Statement> statements, Statement target) {
            for (int index = 0; index < statements.size(); index++) {
                if (statements.get(index) == target) {
                    return index;
                }
            }
            return -1;
        }

        private NodeList<Statement> transform(Statement statement) {
            if (statement.isBlockStmt()) {
                processBlock(statement.asBlockStmt());
                return statements(statement);
            }
            if (statement.isReturnStmt()) {
                return transformReturn(statement.asReturnStmt());
            }
            if (statement.isThrowStmt()) {
                return statements(printStatement(endMarker), statement);
            }
            if (statement.isIfStmt()) {
                return transformIf(statement.asIfStmt());
            }
            if (statement.isWhileStmt()) {
                return transformWhile(statement.asWhileStmt());
            }
            if (statement.isForStmt()) {
                return transformFor(statement.asForStmt());
            }
            if (statement.isForEachStmt()) {
                ForEachStmt forEach = statement.asForEachStmt();
                forEach.setBody(processNestedBody(forEach.getBody()));
                return statements(forEach);
            }
            if (statement.isDoStmt()) {
                DoStmt doStmt = statement.asDoStmt();
                doStmt.setBody(processNestedBody(doStmt.getBody()));
                return statements(doStmt);
            }
            if (statement.isTryStmt()) {
                return transformTry(statement.asTryStmt());
            }
            if (statement.isSwitchStmt()) {
                return transformSwitch(statement.asSwitchStmt());
            }
            if (statement.isSynchronizedStmt()) {
                SynchronizedStmt synchronizedStmt = statement.asSynchronizedStmt();
                processBlock(synchronizedStmt.getBody());
                return statements(synchronizedStmt);
            }
            if (statement.isLabeledStmt()) {
                LabeledStmt labeled = statement.asLabeledStmt();
                labeled.setStatement(processNestedBody(labeled.getStatement()));
                return statements(labeled);
            }
            if (statement.isExpressionStmt()) {
                return transformExpressionStatement(statement.asExpressionStmt());
            }
            return statements(statement);
        }

        private NodeList<Statement> transformReturn(ReturnStmt returnStmt) {
            NodeList<Statement> result = new NodeList<Statement>();
            if (!returnStmt.getExpression().isPresent()) {
                result.add(printStatement("// DEBUG [RETURN] void"));
            } else {
                String temporary = freshName("__debug_return_");
                Expression value = returnStmt.getExpression().get().clone();
                result.add(variableDeclaration(returnType.clone(), temporary, value));
                result.add(logStatement(
                        "// DEBUG [RETURN] ",
                        singletonExpression(new NameExpr(temporary))));
                returnStmt.setExpression(new NameExpr(temporary));
            }
            result.add(printStatement(endMarker));
            result.add(returnStmt);
            return result;
        }

        private NodeList<Statement> transformIf(IfStmt ifStmt) {
            ifStmt.setThenStmt(processNestedBody(ifStmt.getThenStmt()));
            if (ifStmt.getElseStmt().isPresent()) {
                ifStmt.setElseStmt(processNestedBody(ifStmt.getElseStmt().get()));
            }

            Expression condition = ifStmt.getCondition().clone();
            String conditionText = condition.toString();
            String temporary = freshName("__debug_cond_");
            ifStmt.setCondition(new NameExpr(temporary));
            return statements(
                    variableDeclaration(
                            PrimitiveType.booleanType(), temporary, condition),
                    logStatement(
                            "// DEBUG [COND] " + conditionText + " = ",
                            singletonExpression(new NameExpr(temporary))),
                    ifStmt);
        }

        private NodeList<Statement> transformWhile(WhileStmt whileStmt) {
            BlockStmt body = ensureBlock(processNestedBody(whileStmt.getBody()));
            whileStmt.setBody(body);
            Expression condition = whileStmt.getCondition().clone();
            String conditionText = condition.toString();

            if (isTrueLiteral(condition)) {
                body.addStatement(0, logStatement(
                        "// DEBUG [LOOP] " + conditionText + " = ",
                        singletonExpression(new BooleanLiteralExpr(true))));
                return statements(whileStmt);
            }

            String temporary = freshName("__debug_loop_");
            whileStmt.setCondition(new BooleanLiteralExpr(true));
            prependLoopGuard(body, condition, conditionText, temporary);
            return statements(whileStmt);
        }

        private NodeList<Statement> transformFor(ForStmt forStmt) {
            BlockStmt body = ensureBlock(processNestedBody(forStmt.getBody()));
            forStmt.setBody(body);
            if (!forStmt.getCompare().isPresent()) {
                return statements(forStmt);
            }

            Expression condition = forStmt.getCompare().get().clone();
            String conditionText = condition.toString();
            if (isTrueLiteral(condition)) {
                body.addStatement(0, logStatement(
                        "// DEBUG [LOOP] " + conditionText + " = ",
                        singletonExpression(new BooleanLiteralExpr(true))));
                return statements(forStmt);
            }

            String temporary = freshName("__debug_loop_");
            forStmt.setCompare(new BooleanLiteralExpr(true));
            prependLoopGuard(body, condition, conditionText, temporary);
            return statements(forStmt);
        }

        private void prependLoopGuard(
                BlockStmt body,
                Expression condition,
                String conditionText,
                String temporary) {
            if (!condition.findFirst(AssignExpr.class).isPresent()) {
                body.addStatement(0, variableDeclaration(
                        PrimitiveType.booleanType(), temporary, condition));
                body.addStatement(1, logStatement(
                        "// DEBUG [LOOP] " + conditionText + " = ",
                        singletonExpression(new NameExpr(temporary))));
                body.addStatement(2, new IfStmt(
                        new UnaryExpr(
                                new NameExpr(temporary),
                                UnaryExpr.Operator.LOGICAL_COMPLEMENT),
                        StaticJavaParser.parseStatement("break;"),
                        null));
                return;
            }

            NodeList<Statement> originalStatements = body.getStatements();
            body.setStatements(new NodeList<Statement>());

            BlockStmt continueBody = new BlockStmt();
            continueBody.setStatements(originalStatements);
            continueBody.addStatement(0, new ExpressionStmt(new AssignExpr(
                    new NameExpr(temporary),
                    new BooleanLiteralExpr(true),
                    AssignExpr.Operator.ASSIGN)));
            continueBody.addStatement(1, logStatement(
                    "// DEBUG [LOOP] " + conditionText + " = ",
                    singletonExpression(new NameExpr(temporary))));

            BlockStmt exitBody = new BlockStmt();
            exitBody.addStatement(new ExpressionStmt(new AssignExpr(
                    new NameExpr(temporary),
                    new BooleanLiteralExpr(false),
                    AssignExpr.Operator.ASSIGN)));
            exitBody.addStatement(logStatement(
                    "// DEBUG [LOOP] " + conditionText + " = ",
                    singletonExpression(new NameExpr(temporary))));
            exitBody.addStatement(new IfStmt(
                    new UnaryExpr(
                            new NameExpr(temporary),
                            UnaryExpr.Operator.LOGICAL_COMPLEMENT),
                    StaticJavaParser.parseStatement("break;"),
                    null));

            body.addStatement(variableDeclaration(
                    PrimitiveType.booleanType(), temporary));
            body.addStatement(new IfStmt(
                    condition,
                    continueBody,
                    exitBody));
        }

        private NodeList<Statement> transformTry(TryStmt tryStmt) {
            processBlock(tryStmt.getTryBlock());
            for (CatchClause catchClause : tryStmt.getCatchClauses()) {
                processBlock(catchClause.getBody());
            }
            if (tryStmt.getFinallyBlock().isPresent()) {
                processBlock(tryStmt.getFinallyBlock().get());
            }
            return statements(tryStmt);
        }

        private NodeList<Statement> transformSwitch(SwitchStmt switchStmt) {
            for (SwitchEntry entry : switchStmt.getEntries()) {
                processStatementList(entry.getStatements());
            }
            return statements(switchStmt);
        }

        private NodeList<Statement> transformExpressionStatement(ExpressionStmt statement) {
            Expression expression = statement.getExpression();
            if (expression.isVariableDeclarationExpr()) {
                VariableDeclarationExpr declaration = expression.asVariableDeclarationExpr();
                List<String> names = new ArrayList<String>();
                List<Expression> values = new ArrayList<Expression>();
                for (VariableDeclarator variable : declaration.getVariables()) {
                    if (variable.getInitializer().isPresent()
                            && !variable.getNameAsString().startsWith("__debug_")) {
                        names.add(variable.getNameAsString());
                        values.add(new NameExpr(variable.getNameAsString()));
                    }
                }
                if (!names.isEmpty()) {
                    return statements(
                            statement,
                            logStatement(
                                    "// DEBUG [VAR] " + join(names) + " = ", values));
                }
                return statements(statement);
            }

            if (expression.isAssignExpr()) {
                AssignExpr assignment = expression.asAssignExpr();
                String targetText = assignment.getTarget().toString();
                String temporary = freshName("__debug_assignment_");
                Expression snapshot = new BinaryExpr(
                        new StringLiteralExpr(""),
                        new EnclosedExpr(assignment.clone()),
                        BinaryExpr.Operator.PLUS);
                Statement capture = variableDeclaration(
                        StaticJavaParser.parseType("String"),
                        temporary,
                        snapshot);
                if (statement.getComment().isPresent()) {
                    capture.setComment(statement.getComment().get().clone());
                }
                return statements(
                        capture,
                        logStatement(
                                "// DEBUG [VAR] " + targetText + " = ",
                                singletonExpression(new NameExpr(temporary))));
            }
            return statements(statement);
        }

        private Statement processNestedBody(Statement body) {
            if (body.isBlockStmt()) {
                processBlock(body.asBlockStmt());
                return body;
            }
            NodeList<Statement> transformed = transform(body);
            if (transformed.size() == 1) {
                return transformed.get(0);
            }
            BlockStmt block = new BlockStmt();
            block.setStatements(transformed);
            return block;
        }

        private BlockStmt ensureBlock(Statement body) {
            if (body.isBlockStmt()) {
                return body.asBlockStmt();
            }
            return new BlockStmt().addStatement(body);
        }

        private String freshName(String prefix) {
            String candidate;
            do {
                candidate = prefix + temporaryCounter++;
            } while (usedNames.contains(candidate));
            usedNames.add(candidate);
            return candidate;
        }

        private boolean canCompleteNormally(BlockStmt block) {
            if (block.getStatements().isEmpty()) {
                return true;
            }
            return canCompleteNormally(
                    block.getStatement(block.getStatements().size() - 1));
        }

        private boolean canCompleteNormally(Statement statement) {
            if (statement.isReturnStmt() || statement.isThrowStmt()) {
                return false;
            }
            if (statement.isBlockStmt()) {
                return canCompleteNormally(statement.asBlockStmt());
            }
            if (statement.isIfStmt()) {
                IfStmt ifStmt = statement.asIfStmt();
                if (!ifStmt.getElseStmt().isPresent()) {
                    return true;
                }
                return canCompleteNormally(ifStmt.getThenStmt())
                        || canCompleteNormally(ifStmt.getElseStmt().get());
            }
            if (statement.isWhileStmt()) {
                WhileStmt loop = statement.asWhileStmt();
                return !isTrueLiteral(loop.getCondition()) || containsBreak(loop.getBody());
            }
            if (statement.isForStmt()) {
                ForStmt loop = statement.asForStmt();
                boolean infinite = !loop.getCompare().isPresent()
                        || isTrueLiteral(loop.getCompare().get());
                return !infinite || containsBreak(loop.getBody());
            }
            if (statement.isDoStmt()) {
                DoStmt loop = statement.asDoStmt();
                return !isTrueLiteral(loop.getCondition()) || containsBreak(loop.getBody());
            }
            if (statement.isTryStmt()) {
                TryStmt tryStmt = statement.asTryStmt();
                if (tryStmt.getFinallyBlock().isPresent()
                        && !canCompleteNormally(tryStmt.getFinallyBlock().get())) {
                    return false;
                }
                if (canCompleteNormally(tryStmt.getTryBlock())) {
                    return true;
                }
                for (CatchClause catchClause : tryStmt.getCatchClauses()) {
                    if (canCompleteNormally(catchClause.getBody())) {
                        return true;
                    }
                }
                return false;
            }
            if (statement.isSwitchStmt()) {
                return canSwitchCompleteNormally(statement.asSwitchStmt());
            }
            if (statement.isSynchronizedStmt()) {
                return canCompleteNormally(statement.asSynchronizedStmt().getBody());
            }
            if (statement.isLabeledStmt()) {
                LabeledStmt labeled = statement.asLabeledStmt();
                return canCompleteNormally(labeled.getStatement())
                        || containsBreakToLabel(
                                labeled.getStatement(), labeled.getLabel().asString());
            }
            return true;
        }

        private boolean canSwitchCompleteNormally(SwitchStmt switchStmt) {
            boolean hasDefault = false;
            for (SwitchEntry entry : switchStmt.getEntries()) {
                if (entry.getLabels().isEmpty()) {
                    hasDefault = true;
                }
                if (containsBreak(entry.getStatements())) {
                    return true;
                }
                if (entry.getType() != SwitchEntry.Type.STATEMENT_GROUP
                        && canCompleteNormally(entry.getStatements())) {
                    return true;
                }
            }
            if (!hasDefault || switchStmt.getEntries().isEmpty()) {
                return true;
            }
            SwitchEntry last = switchStmt.getEntry(
                    switchStmt.getEntries().size() - 1);
            return canCompleteNormally(last.getStatements());
        }

        private boolean canCompleteNormally(NodeList<Statement> statements) {
            if (statements.isEmpty()) {
                return true;
            }
            return canCompleteNormally(statements.get(statements.size() - 1));
        }

        private boolean containsBreak(NodeList<Statement> statements) {
            for (Statement statement : statements) {
                if (containsBreak(statement)) {
                    return true;
                }
            }
            return false;
        }

        private boolean containsBreak(Statement statement) {
            if (statement.isBreakStmt()) {
                return !statement.asBreakStmt().getLabel().isPresent();
            }
            if (statement.isWhileStmt() || statement.isForStmt()
                    || statement.isForEachStmt() || statement.isDoStmt()
                    || statement.isSwitchStmt()) {
                return false;
            }
            if (statement.isBlockStmt()) {
                return containsBreak(statement.asBlockStmt().getStatements());
            }
            if (statement.isIfStmt()) {
                IfStmt ifStmt = statement.asIfStmt();
                return containsBreak(ifStmt.getThenStmt())
                        || (ifStmt.getElseStmt().isPresent()
                                && containsBreak(ifStmt.getElseStmt().get()));
            }
            if (statement.isTryStmt()) {
                TryStmt tryStmt = statement.asTryStmt();
                if (containsBreak(tryStmt.getTryBlock())) {
                    return true;
                }
                for (CatchClause catchClause : tryStmt.getCatchClauses()) {
                    if (containsBreak(catchClause.getBody())) {
                        return true;
                    }
                }
                return tryStmt.getFinallyBlock().isPresent()
                        && containsBreak(tryStmt.getFinallyBlock().get());
            }
            if (statement.isSynchronizedStmt()) {
                return containsBreak(statement.asSynchronizedStmt().getBody());
            }
            if (statement.isLabeledStmt()) {
                return containsBreak(statement.asLabeledStmt().getStatement());
            }
            return false;
        }

        private boolean containsBreakToLabel(Statement statement, String label) {
            for (BreakStmt breakStmt : statement.findAll(BreakStmt.class)) {
                if (breakStmt.getLabel().isPresent()
                        && breakStmt.getLabel().get().asString().equals(label)) {
                    return true;
                }
            }
            return false;
        }

        private boolean isTrueLiteral(Expression expression) {
            return expression.isBooleanLiteralExpr()
                    && expression.asBooleanLiteralExpr().getValue();
        }

        private Statement variableDeclaration(
                Type type, String name, Expression initializer) {
            VariableDeclarator variable = new VariableDeclarator(
                    type, name, initializer);
            return new ExpressionStmt(new VariableDeclarationExpr(variable));
        }

        private Statement variableDeclaration(Type type, String name) {
            VariableDeclarator variable = new VariableDeclarator(type, name);
            return new ExpressionStmt(new VariableDeclarationExpr(variable));
        }

        private Statement printStatement(String message) {
            return logStatement(message, new ArrayList<Expression>());
        }

        private Statement logStatement(String prefix, List<Expression> values) {
            Expression message = stringLiteral(prefix);
            for (int index = 0; index < values.size(); index++) {
                if (index > 0) {
                    message = new BinaryExpr(
                            message,
                            stringLiteral(","),
                            BinaryExpr.Operator.PLUS);
                }
                message = new BinaryExpr(
                        message,
                        values.get(index).clone(),
                        BinaryExpr.Operator.PLUS);
            }
            FieldAccessExpr systemOut = new FieldAccessExpr(
                    new NameExpr("System"), "out");
            MethodCallExpr println = new MethodCallExpr(systemOut, "println");
            println.addArgument(message);
            return new ExpressionStmt(println);
        }

        private StringLiteralExpr stringLiteral(String value) {
            return new StringLiteralExpr().setString(value);
        }

        private List<Expression> singletonExpression(Expression expression) {
            List<Expression> values = new ArrayList<Expression>();
            values.add(expression);
            return values;
        }

        private String join(List<String> values) {
            StringBuilder result = new StringBuilder();
            for (String value : values) {
                if (result.length() > 0) {
                    result.append(',');
                }
                result.append(value);
            }
            return result.toString();
        }

        private NodeList<Statement> statements(Statement... values) {
            NodeList<Statement> result = new NodeList<Statement>();
            for (Statement value : values) {
                result.add(value);
            }
            return result;
        }
    }
}
