from ent import *
gcd(97,100)
gcd(97 * 10**15, 19**20 * 97**2)              # (2)
primes(10)
primes(45)
trial_division(15)
trial_division(91)
trial_division(11)
trial_division(387833, 300)   
# 300 is not big enough to split off a 
# factor, but 400 is.
trial_division(387833, 400)  
factor(500)
factor(-20)
factor(1)
factor(2004)
xgcd(2,3)
xgcd(10, 12)
g, x, y = xgcd(100, 2004)
inversemod(1,1)
inversemod(2,5)
inversemod(5,8)
inversemod(37,100)
solve_linear(4, 2, 10)
solve_linear(2, 1, 4) == None
crt(1, 2, 3, 4)
crt(4, 5, 10, 3)
crt(-1, -1, 100, 101)
powermod(2,25,30)
powermod(19,12345,100)
primitive_root(7)
primitive_root(389)
primitive_root(5881)
is_pseudoprime(91)
is_pseudoprime(97)
is_pseudoprime(1)
is_pseudoprime(-2)
t = primes(10000)
is_pseudoprime(29341) # first non-prime pseudoprime
factor(29341)
miller_rabin(91)
miller_rabin(97)
t = primes(1000)
random_prime(10)
random_prime(40)
p = random_prime(20)
dh_init(p)
p = random_prime(20)
n, npow = dh_init(p)    
m, mpow = dh_init(p)
dh_secret(p, n, mpow) 
dh_secret(p, m, npow)    
str_to_numlist("Run!", 1000)
str_to_numlist("TOP SECRET", 10**20)
numlist_to_str([82, 117, 110, 33], 1000)
x = str_to_numlist("TOP SECRET MESSAGE", 10**20)
numlist_to_str(x, 10**20)
p = random_prime(20); q = random_prime(20)
e, d, n = rsa_init(p, q)
e
d
n
e = 1413636032234706267861856804566528506075
n = 2109029637390047474920932660992586706589
rsa_encrypt("Run Nikita!", e, n)
rsa_encrypt("Run Nikita!", e, n)
d = 938164637865370078346033914094246201579
n = 2109029637390047474920932660992586706589
msg1 = [1071099761433836971832061585353925961069]
msg2 = [1336506586627416245118258421225335020977]
rsa_decrypt(msg1, d, n)
rsa_decrypt(msg2, d, n)
legendre(2, 5)
legendre(3, 3)
legendre(7, 2003)
sqrtmod(4, 5)              # p == 1 (mod 4)
sqrtmod(13, 23)            # p == 3 (mod 4)
sqrtmod(997, 7304723089)   # p == 1 (mod 4)
convergents([1, 2])
convergents([3, 7, 15, 1, 292])
contfrac_rat(3, 2)
contfrac_rat(103993, 33102)
v, w = contfrac_float(3.14159)
v, w = contfrac_float(2.718)
contfrac_float(0.3)
sum_of_two_squares(5)
sum_of_two_squares(389)
sum_of_two_squares(86295641057493119033)
E = (1, 0, 7)   # y**2 = x**3 + x over Z/7Z
P1 = (1, 3); P2 = (3, 3)
ellcurve_add(E, P1, P2)
ellcurve_add(E, P1, (1, 4))
ellcurve_add(E, "Identity", P2)
E = (1, 0, 7)
P = (1, 3)
ellcurve_mul(E, 5, P)
ellcurve_mul(E, 9999, P)
lcm_to(5)
lcm_to(20)
lcm_to(100)
pollard(5917, lcm_to(5))
pollard(779167, lcm_to(5))
pollard(779167, lcm_to(15))
pollard(187, lcm_to(15))
n = random_prime(5)*random_prime(5)*random_prime(5)
pollard(n, lcm_to(100))
pollard(n, lcm_to(1000))
p = random_prime(20); p
E, P = randcurve(p)
elliptic_curve_method(5959, lcm_to(20))
elliptic_curve_method(10007*20011, lcm_to(100))
p = random_prime(9); q = random_prime(9)
n = p*q; n
elliptic_curve_method(n, lcm_to(100))
elliptic_curve_method(n, lcm_to(500))
p = random_prime(20); p
public, private = elgamal_init(p)
public, private = elgamal_init(random_prime(20))
elgamal_encrypt("RUN", public)
public, private = elgamal_init(random_prime(20))
v = elgamal_encrypt("TOP SECRET MESSAGE!", public)
elgamal_decrypt(v, private)
from ent import *
7/5
-2/3
1.0/3
float(2)/3
100**2
10**20
range(10)            # range(n) is from 0 to n-1       
range(3,10)          # range(a,b) is from a to b-1
[1,2,3] + [5,6,7]    # concatenation
len([1,2,3,4,5])     # length of a list
x = [4,7,10,'gcd']   # mixing types is fine
x[0]                 # 0-based indexing
x[3]
x[3] = 'lagrange'    # assignment
x.append("fermat")   # append to end of list
x
del x[3]             # delete entry 3 from list
x
v = primes(10000)
len(v)    # this is pi(10000)
x=(1, 2, 3)       # creation
x[1]
(1, 2, 3) + (4, 5, 6)  # concatenation
(a, b) = (1, 2)        # assignment assigns to each member
x = 1, 2          # parentheses optional in creation
x
c, d = x          # parentheses also optional 
Q = primes(200000)
factor(162401)
p = random_prime(50)
p
n, npow = dh_init(p)
n
npow
m, mpow = dh_init(p)
m
mpow
dh_secret(p, n, mpow)
dh_secret(p, m, npow)
len(primes(10000))
10000/log(10000)
powermod(3,45,100)
inversemod(37, 112)
powermod(102, 70, 113)
powermod(99, 109, 113)
factor(5352381469067)
d=inversemod(4240501142039, (141307-1)*(37877681-1))
d
convergents([-3,1,1,1,1,3])
convergents([0,2,4,1,8,2])
import math
e = math.exp(1)
v, convs = contfrac_float(e)
factor(12345)
factor(729)
factor(5809961789)
5809961789 % 4
sum_of_two_squares(5809961789)
