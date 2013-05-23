import ent

class Ent:
    def trial_division(self, n, bound=None):
        return ent.trial_division(n, bound=bound)
    def powermod(self, a, m, n):
        return ent.powermod(a, m, n)
    def factor(self, n):
        if n in [-1, 0, 1]: return []
        if n < 0: n = -n
        F = []
        while n != 1:
            p = self.trial_division(n)
            e = 1
            n /= p
            while n%p == 0:
                e += 1; n /= p
            F.append((p,e))
        F.sort()
        return F
    def primitive_root(self, p):
        if p == 2: return 1
        F = self.factor(p-1)
        a = 2
        while a < p:
            generates = True
            for q, _ in F:
                if self.powermod(a, (p-1)/q, p) == 1:
                    generates = False
                    break
            if generates: return a
            a += 1
        assert False, "p must be prime."

