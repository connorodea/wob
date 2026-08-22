"""Built-in course packs: famous university courses -> canonical books.

Each pack references books by the SAME token tuples as curated.py, so
`wob coursepack <id>` can score against local deals without new taxonomy.
"""

# (course id, display name, [(book label, token list), ...])
COURSEPACKS = {
    "stanford-cs229": (
        "Stanford CS229 Machine Learning",
        [
            ("Pattern Recognition and Machine Learning (Bishop)", ["bishop", "pattern", "recognition"]),
            ("The Elements of Statistical Learning (Hastie)", ["hastie", "elements", "statistical", "learning"]),
            ("An Introduction to Statistical Learning (James)", ["james", "introduction", "statistical", "learning"]),
            ("Deep Learning (Goodfellow)", ["goodfellow", "deep", "learning"]),
            ("Machine Learning (Mitchell)", ["mitchell", "machine", "learning"]),
            ("Probabilistic Machine Learning (Murphy)", ["murphy", "probabilistic", "machine", "learning"]),
        ],
    ),
    "stanford-cs231n": (
        "Stanford CS231n Deep Learning for Computer Vision",
        [
            ("Deep Learning (Goodfellow)", ["goodfellow", "deep", "learning"]),
            ("Computer Vision: Algorithms and Applications (Szeliski)", ["szeliski", "computer", "vision"]),
            ("Deep Learning with PyTorch (Stevens)", ["stevens", "deep", "learning", "pytorch"]),
            ("Deep Learning with Python (Chollet)", ["chollet", "deep", "learning", "python"]),
        ],
    ),
    "mit-6-036": (
        "MIT 6.036 Machine Learning",
        [
            ("Pattern Recognition and Machine Learning (Bishop)", ["bishop", "pattern", "recognition"]),
            ("Machine Learning (Mitchell)", ["mitchell", "machine", "learning"]),
            ("The Elements of Statistical Learning (Hastie)", ["hastie", "elements", "statistical", "learning"]),
            ("Mathematics for Machine Learning (Deisenroth)", ["deisenroth", "mathematics", "machine", "learning"]),
        ],
    ),
    "mit-6-s191": (
        "MIT 6.S191 Intro to Deep Learning",
        [
            ("Deep Learning (Goodfellow)", ["goodfellow", "deep", "learning"]),
            ("Deep Learning with Python (Chollet)", ["chollet", "deep", "learning", "python"]),
            ("Python Machine Learning (Raschka)", ["raschka", "python", "machine", "learning"]),
        ],
    ),
    "berkeley-cs188": (
        "Berkeley CS188 Intro to AI",
        [
            ("Artificial Intelligence: A Modern Approach (Russell & Norvig)", ["russell", "artificial", "intelligence", "modern", "approach"]),
            ("The Elements of Statistical Learning (Hastie)", ["hastie", "elements", "statistical", "learning"]),
        ],
    ),
    "harvard-cs50": (
        "Harvard CS50",
        [
            ("Algorithms (Sedgewick)", ["sedgewick", "algorithms"]),
            ("Introduction to the Theory of Computation (Sipser)", ["sipser", "introduction", "theory", "computation"]),
            ("Computer Science: An Overview (Brookshear)", ["brookshear", "computer", "science", "overview"]),
        ],
    ),
    "mit-18-06": (
        "MIT 18.06 Linear Algebra",
        [
            ("Linear Algebra and Learning from Data (Strang)", ["strang", "linear", "algebra", "learning", "data"]),
            ("Introduction to Applied Linear Algebra (Boyd)", ["boyd", "introduction", "applied", "linear", "algebra"]),
            ("Matrix Analysis (Horn)", ["horn", "matrix", "analysis"]),
        ],
    ),
    "stanford-cs124": (
        "Stanford CS124 From Languages to Information",
        [
            ("Speech and Language Processing (Jurafsky & Martin)", ["jurafsky", "speech", "language", "processing"]),
            ("Foundations of Statistical NLP (Manning)", ["manning", "foundations", "statistical", "natural", "language"]),
            ("Introduction to Information Retrieval (Manning)", ["manning", "introduction", "information", "retrieval"]),
            ("Deep Learning with Python (Chollet)", ["chollet", "deep", "learning", "python"]),
        ],
    ),
    "deepmind-rl": (
        "Reinforcement Learning (Sutton & Barto track)",
        [
            ("Reinforcement Learning: An Introduction (Sutton & Barto)", ["sutton", "reinforcement", "learning", "introduction"]),
            ("Bandit Algorithms (Lattimore)", ["lattimore", "bandit", "algorithms"]),
            ("Algorithms for Reinforcement Learning (Szepesvari)", ["szepesvari", "algorithms", "reinforcement", "learning"]),
            ("Reinforcement Learning and Optimal Control (Bertsekas)", ["bertsekas", "reinforcement", "optimal", "control"]),
        ],
    ),
    "data-science-101": (
        "Applied Data Science starter shelf",
        [
            ("Python Data Science Handbook (VanderPlas)", ["vanderplas", "python", "data", "science", "handbook"]),
            ("Data Science from Scratch (Grus)", ["grus", "data", "science", "scratch"]),
            ("Practical Statistics for Data Scientists (Bruce)", ["bruce", "practical", "statistics", "data", "scientists"]),
            ("Python for Data Analysis (McKinney)", ["mckinney", "python", "data", "analysis"]),
            ("R for Data Science (Wickham)", ["wickham", "r", "data", "science"]),
        ],
    ),
    "stats-101": (
        "Statistics foundations",
        [
            ("All of Statistics (Wasserman)", ["wasserman", "all", "statistics"]),
            ("Statistical Rethinking (McElreath)", ["mcelreath", "statistical", "rethinking"]),
            ("The Art of Statistics (Spiegelhalter)", ["spiegelhalter", "art", "statistics"]),
            ("Computer Age Statistical Inference (Efron)", ["efron", "computer", "age", "statistical", "inference"]),
            ("Naked Statistics (Wheelan)", ["wheelan", "naked", "statistics"]),
        ],
    ),
    "causal-inference": (
        "Causal inference seminar",
        [
            ("The Book of Why (Pearl)", ["pearl", "book", "why"]),
            ("Causal Inference in Statistics (Pearl)", ["pearl", "causal", "inference", "statistics"]),
            ("Mostly Harmless Econometrics (Angrist & Pischke)", ["angrist", "mostly", "harmless"]),
            ("Causal Inference: The Mixtape (Cunningham)", ["cunningham", "causal", "inference"]),
        ],
    ),
    "graph-ml": (
        "Graph ML reading group",
        [
            ("Graph Representation Learning (Hamilton)", ["hamilton", "graph", "representation", "learning"]),
            ("Deep Learning on Graphs (Ma)", ["deep", "learning", "graphs"]),
            ("Geometric Deep Learning (Bronstein)", ["bronstein", "geometric", "deep", "learning"]),
            ("Probabilistic Graphical Models (Koller)", ["koller", "probabilistic", "graphical", "models"]),
        ],
    ),
    "generative-ai": (
        "Generative AI study group",
        [
            ("Deep Generative Modeling (Tomczak)", ["tomczak", "deep", "generative"]),
            ("Generative Deep Learning (Foster)", ["foster", "generative", "deep"]),
            ("An Introduction to Variational Autoencoders (Kingma)", ["kingma", "variational", "autoencoders"]),
            ("Normalizing Flows (Papamakarios)", ["papamakarios", "normalizing", "flows"]),
            ("GANs in Action (Langr)", ["langr", "gans", "action"]),
        ],
    ),
    "mlops": (
        "ML engineering on the job",
        [
            ("Designing Machine Learning Systems (Huyen)", ["huyen", "designing", "machine", "learning", "systems"]),
            ("Designing Data-Intensive Applications (Kleppmann)", ["kleppmann", "data", "intensive", "applications"]),
            ("Machine Learning Design Patterns (Lakshmanan)", ["machine", "learning", "design", "patterns"]),
            ("Feature Engineering for ML (Zheng)", ["zheng", "feature", "engineering", "machine", "learning"]),
        ],
    ),
    "pl-types": (
        "Programming Languages and Type Systems",
        [
            ("Types and Programming Languages (Pierce)", ['pierce', 'types', 'programming', 'languages']),
            ("Practical Foundations for Programming Languages (Harper)", ['harper', 'practical', 'foundations', 'programming', 'languages']),
            ("Programming Language Pragmatics (Scott)", ['scott', 'programming', 'language', 'pragmatics']),
            ("Concepts in Programming Languages (Mitchell)", ['mitchell', 'concepts', 'programming', 'languages']),
            ("Advanced Topics in Types and Programming Languages (Pierce)", ['pierce', 'advanced', 'topics', 'types', 'programming', 'languages']),
        ],
    ),
    "ds-algorithms": (
        "Algorithm Design (Kleinberg)",
        [
            ("Algorithm Design (Kleinberg)", ['kleinberg', 'algorithm', 'design']),
            ("Algorithms (Dasgupta)", ['dasgupta', 'algorithms']),
            ("Data Structures and Algorithm Analysis in Java (Weiss)", ['weiss', 'data', 'structures', 'algorithm', 'analysis']),
            ("Algorithm Design Manual (Skiena)", ['skiena', 'algorithm', 'design', 'manual']),
            ("Algorithms (Erickson)", ['erickson', 'algorithms']),
        ],
    ),
    "calc-course": (
        "Calculus & Real Analysis",
        [
            ("Calculus (Spivak)", ['spivak', 'calculus']),
            ("Understanding Analysis (Abbott)", ['abbott', 'understanding', 'analysis']),
            ("The Calculus Lifesaver (Banner)", ['banner', 'calculus', 'lifesaver']),
        ],
    ),
    "compiler-construction": (
        "Compiler Construction",
        [
            ("Engineering a Compiler (Cooper)", ['cooper', 'engineering', 'compiler']),
            ("Modern Compiler Implementation in Java (Appel)", ['appel', 'modern', 'compiler', 'implementation']),
            ("Compiler Construction: Principles and Practice (Louden)", ['louden', 'compiler', 'construction', 'principles', 'practice']),
            ("Advanced Compiler Design and Implementation (Muchnick)", ['muchnick', 'advanced', 'compiler', 'design', 'implementation']),
            ("Parsing Techniques: A Practical Guide (Grune)", ['grune', 'parsing', 'techniques', 'practical', 'guide']),
        ],
    ),
    "db-course": (
        "Database Systems",
        [
            ("Database System Concepts (Silberschatz)", ['silberschatz', 'database', 'system', 'concepts']),
            ("Fundamentals of Database Systems (Elmasri)", ['elmasri', 'fundamentals', 'database', 'systems']),
            ("Database Systems: The Complete Book (Garcia-Molina)", ['garcia-molina', 'database', 'systems', 'complete', 'book']),
            ("Readings in Database Systems (Hellerstein)", ['hellerstein', 'readings', 'database', 'systems']),
            ("Transaction Processing: Concepts and Techniques (Gray)", ['gray', 'transaction', 'processing']),
        ],
    ),
    "discrete-math-cs": (
        "Discrete Mathematics for Computer Science",
        [
            ("Discrete Mathematics and Its Applications (Rosen)", ['rosen', 'discrete', 'mathematics', 'applications']),
            ("Discrete Mathematics with Applications (Epp)", ['epp', 'discrete', 'mathematics', 'applications']),
            ("Discrete and Combinatorial Mathematics (Grimaldi)", ['grimaldi', 'discrete', 'combinatorial', 'mathematics']),
            ("Discrete Mathematics (Johnsonbaugh)", ['johnsonbaugh', 'discrete', 'mathematics']),
        ],
    ),
    "distributed-course": (
        "Distributed Systems",
        [
            ("Designing Data-Intensive Applications (Kleppmann)", ['kleppmann', 'designing', 'data-intensive', 'applications']),
            ("Distributed Systems (van Steen)", ['van steen', 'distributed', 'systems']),
            ("Understanding Distributed Systems (Vitillo)", ['vitillo', 'understanding', 'distributed', 'systems']),
            ("Designing Distributed Systems (Burns)", ['burns', 'designing', 'distributed', 'systems']),
        ],
    ),
    "econ-cs": (
        "Algorithmic Game Theory",
        [
            ("Algorithmic Game Theory (Nisan)", ['nisan', 'algorithmic', 'game', 'theory']),
            ("Multiagent Systems (Shoham)", ['shoham', 'multiagent', 'systems']),
            ("Prediction, Learning, and Games (Cesa-Bianchi)", ['cesa-bianchi', 'prediction', 'learning', 'games']),
            ("Networks, Crowds, and Markets (Easley)", ['easley', 'networks', 'crowds', 'markets']),
        ],
    ),
    "embedded-systems": (
        "Embedded Systems and Microcontrollers",
        [
            ("Embedded Systems: Real-Time Interfacing to ARM Cortex-M Microcontrollers (Valvano)", ['valvano', 'interfacing', 'arm', 'cortex']),
            ("The 8051 Microcontroller and Embedded Systems (Mazidi)", ['mazidi', '8051', 'microcontroller']),
            ("An Embedded Software Primer (Simon)", ['simon', 'software', 'primer']),
            ("Programming Embedded Systems (Barr)", ['barr', 'programming', 'systems']),
            ("Making Embedded Systems (White)", ['white', 'making']),
            ("The Definitive Guide to ARM Cortex-M3 and Cortex-M4 Processors (Yiu)", ['yiu', 'definitive', 'guide', 'arm', 'cortex']),
        ],
    ),
    "hci-design": (
        "Human Computer Interaction and Design",
        [
            ("The Design of Everyday Things (Norman)", ['norman', 'design', 'everyday', 'things']),
            ("Interaction Design: Beyond Human-Computer Interaction (Preece)", ['preece', 'interaction', 'design', 'beyond', 'human', 'computer']),
            ("Designing Interactive Systems: A Comprehensive Guide to HCI, UX and Interaction Design (Benyon)", ['benyon', 'designing', 'interactive', 'systems', 'comprehensive', 'guide', 'hci', 'ux']),
            ("Human-Computer Interaction (Dix)", ['dix', 'human', 'computer', 'interaction']),
            ("Designing the User Interface: Strategies for Effective Human-Computer Interaction (Shneiderman)", ['shneiderman', 'designing', 'user', 'interface', 'strategies', 'effective']),
            ("Usability Engineering (Nielsen)", ['nielsen', 'usability', 'engineering']),
        ],
    ),
    "intro-cs": (
        "Intro CS classics",
        [
            ("How to Design Programs (Felleisen)", ['felleisen', 'how', 'design', 'programs']),
            ("The Little Schemer (Friedman)", ['friedman', 'little', 'schemer']),
            ("Computer Systems: A Programmer's Perspective (Bryant)", ['bryant', 'computer', 'systems', 'programmer', 'perspective']),
            ("Structure and Interpretation of Computer Programs (Abelson)", ['abelson', 'structure', 'interpretation', 'computer', 'programs']),
        ],
    ),
    "networks-course": (
        "Computer Networks",
        [
            ("Computer Networking: A Top-Down Approach (Kurose)", ['kurose', 'computer', 'networking', 'top-down', 'approach']),
            ("Computer Networks: A Systems Approach (Peterson)", ['peterson', 'computer', 'networks', 'systems', 'approach']),
            ("TCP/IP Illustrated Vol 1 (Stevens)", ['stevens', 'tcp', 'illustrated']),
        ],
    ),
    "numerics-course": (
        "Numerical Methods",
        [
            ("Fundamentals of Numerical Computation (Trefethen)", ['trefethen', 'numerical', 'computation']),
            ("Scientific Computing: An Introductory Survey (Heath)", ['heath', 'scientific', 'computing']),
            ("Numerical Methods for Engineers (Chapra)", ['chapra', 'numerical', 'methods', 'engineers']),
        ],
    ),
    "os-course": (
        "Operating Systems",
        [
            ("Operating Systems: Three Easy Pieces (Arpaci-Dusseau)", ['arpaci-dusseau', 'three', 'easy', 'pieces']),
            ("Modern Operating Systems (Tanenbaum)", ['tanenbaum', 'modern', 'operating', 'systems']),
            ("Operating System Concepts (Silberschatz)", ['silberschatz', 'operating', 'system', 'concepts']),
            ("Computer Systems: A Programmer's Perspective (Bryant)", ['bryant', 'computer', 'systems', 'programmer', 'perspective']),
        ],
    ),
    "probability-and-randomness-for-cs": (
        "Probability and Randomness for CS",
        [
            ("A First Course in Probability (Ross)", ['ross', 'first', 'course', 'probability']),
            ("An Introduction to Probability Theory and Its Applications (Feller)", ['feller', 'introduction', 'probability', 'theory', 'applications']),
            ("Probability: Theory and Examples (Durrett)", ['durrett', 'probability', 'theory', 'examples']),
            ("Probability and Computing (Mitzenmacher)", ['mitzenmacher', 'probability', 'computing']),
            ("Randomized Algorithms (Motwani)", ['motwani', 'randomized', 'algorithms']),
            ("Probability and Random Processes (Grimmett)", ['grimmett', 'probability', 'random', 'processes']),
        ],
    ),
    "security-course": (
        "Computer Security",
        [
            ("Security Engineering (Anderson)", ['anderson', 'security', 'engineering']),
            ("Applied Cryptography (Schneier)", ['schneier', 'applied', 'cryptography']),
            ("Serious Cryptography (Aumasson)", ['aumasson', 'serious', 'cryptography']),
            ("Web Security for Developers (McDonald)", ['mcdonald', 'web', 'security', 'developers']),
        ],
    ),
    "signals-and-systems": (
        "Signals and Systems / Digital Signal Processing",
        [
            ("Signals and Systems (Oppenheim)", ['oppenheim', 'signals', 'systems']),
            ("Discrete-Time Signal Processing (Oppenheim & Schafer)", ['oppenheim', 'discrete', 'time', 'signal', 'processing']),
            ("Digital Signal Processing (Proakis & Manolakis)", ['proakis', 'digital', 'signal', 'processing']),
            ("Digital Signal Processing: A Computer-Based Approach (Mitra)", ['mitra', 'computer', 'based', 'approach']),
            ("Understanding Digital Signal Processing (Lyons)", ['lyons', 'understanding', 'digital']),
            ("Signals and Systems: Continuous and Discrete (Ziemer & Tranter)", ['ziemer', 'continuous', 'discrete']),
        ],
    ),
    "software-arch": (
        "Software Architecture",
        [
            ("A Philosophy of Software Design (Ousterhout)", ['ousterhout', 'philosophy', 'software', 'design']),
            ("Software Architecture in Practice (Bass)", ['bass', 'software', 'architecture', 'practice']),
            ("Building Evolutionary Architectures (Ford)", ['ford', 'building', 'evolutionary', 'architectures']),
        ],
    ),
    "swe-course": (
        "Software Engineering",
        [
            ("Software Engineering (Sommerville)", ['sommerville', 'software', 'engineering']),
            ("The Mythical Man-Month (Brooks)", ['brooks', 'mythical', 'man', 'month']),
            ("Code Complete (McConnell)", ['mcconnell', 'code', 'complete']),
            ("Accelerate (Forsgren)", ['forsgren', 'accelerate']),
        ],
    ),
    "theory-cs": (
        "Theory of Computation",
        [
            ("Introduction to the Theory of Computation (Sipser)", ['sipser', 'introduction', 'theory', 'computation']),
            ("Introduction to Automata Theory, Languages, and Computation (Hopcroft)", ['hopcroft', 'introduction', 'automata', 'theory']),
            ("Computational Complexity: A Modern Approach (Arora)", ['arora', 'computational', 'complexity']),
            ("The Nature of Computation (Moore)", ['moore', 'nature', 'computation']),
        ],
    ),
}


def list_coursepacks():
    return sorted(COURSEPACKS.items())


def get_coursepack(course_id):
    hit = COURSEPACKS.get(course_id)
    if not hit:
        matches = [k for k in COURSEPACKS if course_id.lower() in k]
        if len(matches) == 1:
            hit = COURSEPACKS[matches[0]]
            course_id = matches[0]
    return (course_id, hit) if hit else (None, None)


def match_deals(rows, tokens):
    """Return deals (cheapest-first) whose title+handle+author contain ALL tokens."""
    from .curated import _norm_multi

    norm_toks = tuple(_norm_multi(*tokens).split())
    out = []
    for r in rows:
        hay = _norm_multi(r.get("title", ""), r.get("handle", ""), r.get("author", ""))
        if all(t in hay for t in norm_toks):
            out.append(r)
    out.sort(key=lambda r: (r["used_price"] if r.get("used_price") else 1e9))
    return out