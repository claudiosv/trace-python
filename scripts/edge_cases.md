# Edge cases
For heuristic source retrieval, because it's just hacked together grep, not all methods have their signature exposed.

## If the method name is not in the first 3 lines of the grep output but...
### the class name is e.g. DeletingPathVisitor present or the first line is a comment:
```java
            # THIS IS A PROBLEM, but not one for now, notice the visitFile method name but it is deep in the class
            Analyzing FQN: org.apache.commons.io.file.DeletingPathVisitor:visitFile
                Heuristic source: /Users/claudio/projects/binarydecomp/Jackal/repos/commons-io/src/main/java/org/apache/commons/io/file/DeletingPathVisitor.java
                    Anonymous methods: []
                    Anonymous classes: []
                    One liner ([37])
                         -> Something went wrong! 3
            36  */
            37 public class DeletingPathVisitor extends CountingPathVisitor {
            # Here the problem is that the method def is too high up due to comments
    Analyzing FQN: org.apache.commons.io.output.DeferredFileOutputStream:toInputStream
    Heuristic source: /Users/claudio/projects/binarydecomp/Jackal/repos/commons-io/src/main/java/org/apache/commons/io/output/DeferredFileOutputStream.java
        Anonymous methods: []
        Anonymous classes: []
        8 / 3 lines ([271, 275, 278])
             -> Something went wrong! 3
269         // but we should force the habit of closing whether we are working with
270         // a file or memory.
271         if (!closed) {
272             throw new IOException("Stream not closed");
273         }
274
275         if (isInMemory()) {
276             return memoryOutputStream.toInputStream();
277         }
278         return Files.newInputStream(outputPath);
```

### a lambda and `->` is present:
"""
        Analyzing FQN: org.apache.commons.io.input.CharacterFilterReader:lambda$new$0
            Heuristic source: /Users/claudio/projects/binarydecomp/Jackal/repos/commons-io/src/main/java/org/apache/commons/io/input/CharacterFilterReader.java
                Anonymous methods: ['new', '0']
                Anonymous classes: []
                One liner ([38])
                     -> Something went wrong! 3
        37     public CharacterFilterReader(final Reader reader, final int skip) {
        38         super(reader, c -> c == skip);
```