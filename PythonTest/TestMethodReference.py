class TestMethodReference:
    def __init__(self):
        self.method = 0

    def methodFunction(self):
        print("Method called!")


method1 = TestMethodReference()
reference = method1.methodFunction
print(reference)
reference()