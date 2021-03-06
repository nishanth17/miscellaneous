"""
    This module contains highly efficient routines to find integral solutions 
    to quadratic Diophantine equations of the form ax^2 + bxy + cy^2 + dx + ey 
    + f = 0 where a, b, c, d, e, and f are constants. This was mostly adapted 
    from Laurent Mazare's version of the same which can be found at 
    https://github.com/LaurentMazare/ProjectEuler/blob/master/dioph.py

    
    NOTE: This is a work in progress and will be completed sometime in the future.
    
    References:
    (i) John Robertson; "Matthews’ Method for Solving ax2 + bxy + cy2 = N"
    (ii) John Robertson; "Solving the generalized Pell equation"
    (iii) John Robertson; "Solving the equation ax2 + bxy + cy2 + dx + ey + f = 0"
"""

"""
    TODO List:
    -> Fix the Cornacchia thing (ax^2 + by^2 = n) or re-write it since it doesn't 
       find all solutions - Using the BQF algorithm for this acually produces better results. 
    -> If n = 1, we have a problem with its factorization so deal with this case 
       separately.
    -> Test this thing. 
"""


import mod_sqrt
import tools
from math import sqrt, floor
from time import time
import fractions
import math


#####################
# Utility Functions #
#####################

""" 
    Returns the GCD of x and y 
"""
def gcd(x, y):
    if x == 1 or y == 1: return 1
    x, y = abs(x), abs(y)
    while y:
        x, y = y, x % y
    return x


""" 
    Returns (d, x, y) such that ax + by = d where d = gcd(a, b) 
"""
def extended_gcd(a, b):
    x, y, u, v = 0, 1, 1, 0
    while a != 0:
        q, r = b // a, tools.mod(b, a)
        m, n = x - u * q, y - v * q
        b, a, x, y, u, v = a, r, u, v, m, n
    return b, y, x


""" 
    Returns the modular inverse of a w.r.t to b 
"""
def mod_inverse(a, b):
    return extended_gcd(a, b)[2]


def sqrt_int(x):
    if x < 0: return -1
    s = int(sqrt(x))
    return s if s*s == x else -1


""" 
    Returns the convergents of the continued fraction expansion for
    (p0+sqrt(d))/q0 and a bunch of other stuff 
"""
def pqa(p0, q0, d, gen_second_period = False):
    assert 0 < d, "d cannot be negative or zero"
    assert q0 != 0, "q0 cannot be zero"
    assert (p0*p0 - d) % q0 == 0, "p0^2 cannot be different from d modulo q0"
    
    sqrt_d = sqrt(d)
    assert int(sqrt_d) * int(sqrt_d) != d, "d cannot be a perfect square"
    
    a_i, a_im = 1, 0
    b_i, b_im = 0, 1
    g_i, g_im = q0, -p0
    p_i, q_i = p0, q0
    i, ir = -1, None
    
    ps, qs, alphas = [], [], []
    a_list, bs, gs = [], [], []
    
    while True:
        i += 1
        xi_i = (p_i + sqrt_d)/q_i
        xibar_i = (p_i - sqrt_d)/q_i
        alpha_i = int(floor(xi_i))
        a_i, a_im = alpha_i * a_i + a_im, a_i
        b_i, b_im = alpha_i * b_i + b_im, b_i
        g_i, g_im = alpha_i * g_i + g_im, g_i
        
        # Cycle begins
        if ir == None and 1 < xi_i and -1 < xibar_i and xibar_i < 0:           
            ir, p_ir, q_ir = i, p_i, q_i

        # Cycle ends - generate second period if necessary
        if ir != None and ir != i and p_i == p_ir and q_i == q_ir:
            # Go one period ahead
            if gen_second_period:
                for _ in range(i - ir):
                    ps.append(p_i); qs.append(q_i); alphas.append(alpha_i)
                    a_list.append(a_i); bs.append(b_i); gs.append(g_i)
                    p_i = alpha_i * q_i - p_i
                    q_i = (d - p_i * p_i) / q_i

                    xi_i = (p_i + sqrt_d)/q_i
                    alpha_i = int(floor(xi_i))
                    a_i, a_im = alpha_i * a_i + a_im, a_i
                    b_i, b_im = alpha_i * b_i + b_im, b_i
                    g_i, g_im = alpha_i * g_i + g_im, g_i
            break
    
        ps.append(p_i); qs.append(q_i); alphas.append(alpha_i)
        a_list.append(a_i); bs.append(b_i); gs.append(g_i)
                
        # Update p_i and q_i for i+1
        p_i = alpha_i * q_i - p_i
        q_i = (d - p_i * p_i) / q_i

    return ps, qs, alphas, a_list, bs, gs, ir, i - ir


""" 
    Returns (alpha, beta, gamma, delta) such that gcd(alpha, gamma)
    = 1, gcd(A, N) = 1, and (alpha*delta - beta*gamma) = 1 where
    A = a*alpha**2 + b*alpha*gamma + c*gamma**2.
"""
def find_unimodular_transform(a, b, c, n, alpha_guess = 1):
    alpha, gamma, beta, delta = alpha_guess, 1, -1, 0
    f = lambda alpha, gamma: a*alpha*alpha + b*alpha*gamma \
        + c*gamma*gamma
    
    # Incrementally find gamma - this is a weird hack but it works
    prev_g1, prev_g2 = 1, 1
    while True:
        g1 = gcd(alpha, gamma)
        g2 = gcd(f(alpha, gamma), n)
        
        if g1 == 1 and g2 == 1:
            break
        if g1 == prev_g1 or g2 == prev_g2:
            alpha += 1
        else:
            gamma += 1
        
        prev_g1, prev_g2 = g1, g2
    
    if alpha == 1:
        # Pick x and y in this case
        beta, delta = -1, 0
    else:
        # This reduces to solving ax - by = 1
        beta = mod_inverse(tools.mod(-gamma, alpha), alpha)
        delta = (beta * gamma + 1) / alpha
    
    return alpha, beta, gamma, delta


""" 
    Gauss' reduction algorithm i.e. returns the reduced form of the binary
    quadratic form ax^2 + bxy + cy^2 along with the transformation coefficients. 
"""
def find_reduced_form(a, b, c):
    alpha, beta, gamma, delta = 1, 0, 0, 1
    
    # Continue until we find the reduced form
    while -a < b <= a < c or 0 <= b <= a == c:
        if c < a or (b < 0 and c == a):
            # x, y -> -y, x
            a, b, c = c, -b, a
            alpha, beta, gamma, delta = -gamma, -delta, alpha, beta
        else:
            # x, y -> x + ky, y; k = (b'-b)/2a, b' = b (mod 2a)
            b_prime = tools.mod(b, 2*a)
            
            if b_prime > a:
                b_prime -= 2*a
            
            k = (b_prime - b) // (2*a)
            b, c = b_prime, a*k*k + b*k + c
            alpha, beta = alpha + gamma * k, beta + delta * k
    
    return a, b, c, delta, beta, gamma, alpha


""" 
    Reconstructs divisors that are perfect squares and their
    factorizations from the prime factorization of a number.
    The squares and their respective prime factorizations are
    stored in a dictionary with the numbers and their respective
    factorization as the keys and values respectively. 
"""
def list_square_divs(n, fact_m, div, pos, div_dict):
    div_dict[n] = div
    for i in range(pos, len(fact_m)):
        p, pow, pow_p = fact_m[i][0], fact_m[i][1], 1
        
        for pow2 in range(2, pow + 1, 2):
            pow_p *= p * p
            if div and div[-1][0] == p:
                new_div = div[0 : len(div) - 1] + [(p, pow2)]
            else:
                new_div = div + [(p, pow2)]
        
            list_square_divs(n * pow_p, fact_m[:i] + [(p, pow - pow2)] + \
                             fact_m[i + 1:], new_div, i, div_dict)


""" 
    Returns C = AxB where A and B are 2x2 matrices 
"""
def matrix_multiply_2x2(A, B):
    C00 = A[0][0]*B[0][0] + A[0][1]*B[1][0]
    C01 = A[0][0]*B[0][1] + A[0][1]*B[1][1]
    C10 = A[1][0]*B[0][0] + A[1][1]*B[1][0]
    C11 = A[1][0]*B[0][1] + A[1][1]*B[1][1]
    return [[C00, C01], [C10, C11]]


""" 
    Returns C = Av where A is a 2x2 matrix and v is a 2x1 vector 
"""
def matrix_vector_multiply_2x2(A, v):
    C0 = A[0][0]*v[0] + A[0][1]*v[1]
    C1 = A[1][0]*v[0] + A[1][1]*v[1]
    return [C0, C1]


""" 
    Returns C = A+B where A and B are 2x1 vectors 
"""
def vector_vector_add_2x1(A, v):
    C0 = A[0] + B[0]
    C1 = A[1] + B[1]
    return [C0, C1]


#############################################
# Linear Diophantine Equation : ax + by = c #
#############################################


""" 
    Returns all solutions to ax + by = c such that |x| <= max_x or
    |y| <= max_x if b = 0. 
"""
def dioph_linear(a, b, c):
    assert c != 0, "Invalid coefficients"
    
    sols = []
    # a = 0 or b = 0; this reduces to a univariate linear equation
    if b == 0:
        if tools.mod(c, abs(a)) == 0:
            x = c / a
            for y in range(-abs(max_x), abs(max_x) + 1):
                sols.append((x, y))
        return sols
    elif a == 0:
        if tools.mod(c, abs(b)) == 0:
            y = c / b
            for x in range(-abs(max_x), abs(max_x) + 1):
                sols.append((x, y))
        return sols

    g = gcd(a, b)
    
    # There aren't any solutions in this case; the proof is
    # straightforward
    if tools.mod(c, g) != 0:
        return sols

    d, y, x = extended_gcd(a, b)
    x, y = x * c/d, y * c/d
    u, v = a/g, b/g

    k_min, k_max = (-x - max_x) // v + 1, (max_x - x) // v
    for k in range(k_min, k_max + 1):
        sols.append((x + k*v, y - k*u))

    return sols


#######################################################
# Bivariate Second Order Equation : axy + bx + cy = d #
#######################################################


""" 
    Returns solutions to axy + bx + cy + d = 0 where a != 0 and |x| <= max_x. 
    This reduces to solving (ax + c)(ay + b) = bc - da. Thus, either there
    are an infinite number, no solutions (if bc - da = 0), or there are a
    finite number of solutions (bc - da =/= 0) 
"""
def dioph_simple_hyperbolic(a, b, c, d, max_x = 0):
    assert a != 0, "Invalid coefficients"

    sols = []
    d = -d; delta = b*c - d*a
    
    if delta == 0:
        if tools.mod(c, a) == 0:
            # Note there are an infinite number of solution of the
            # form (-c/a, y) where y is any integer. I just choose
            # to include one of them in this case. 
            sols.append((-c/a, 0))

        if tools.mod(b, a) == 0:
            # Include all solutions of the form (x, -b/a) such that
            # |x| <= max_x. 
            y = -b / a
            for x in range(-max_x, max_x + 1):
                sols.append((x, y))
    else:
        sols = set([])
        divs = tools.divisors(abs(delta))
            
        for div in divs:
            # Case 1 - div > 0
            x, y = div - c, delta/div - b
            if tools.mod(x, a) == 0 and tools.mod(y, a) == 0:
                if not max_x:
                    sols.add((x/a, y/a))
                    continue
                if x/a <= max_x:
                    sols.add((x/a, y/a))
            
            # Case 2 - div < 0
            div = -div
            x, y = div - c, delta/div - b
            if tools.mod(x, a) == 0 and tools.mod(y, a) == 0:
                if not max_x:
                    sols.add((x/a, y/a))
                    continue
                if x/a <= max_x:
                    sols.add((x/a, y/a))

    return list(sols)


#########################################################
# Pell's Equation and Generalizations : ax^2 - by^2 = n #
#########################################################


""" 
    Get the minimal solution for x^2 - dy^2 = epsilon, where epsilon can be 1 or -1
"""
def pell1_min(d, epsilon):
    assert epsilon == 1 or epsilon == -1, "epsilon is neither -1 or 1"
    temp = pqa(0, 1, d)
    alphas, l = temp[2], temp[-1]

    if l & 1: # l is even
        index = 2*l - 1 if epsilon == 1 else l-1
    else: # l is odd
        if epsilon == -1: return None
        index = l - 1

    b_i, b_im = 0, 1
    g_i, g_im = 1, 0
    pre_l = len(alphas) - l

    for i in xrange(0, 1 + index):
        pos = i if i < pre_l else pre_l + (i - pre_l) % l
        alpha_i = alphas[pos]
        b_i, b_im = alpha_i * b_i + b_im, b_i
        g_i, g_im = alpha_i * g_i + g_im, g_i

    return g_i, b_i


""" 
    Get the minimal solution for x^2 - dy^2 = 4*epsilon, where
    epsilon can be 1 or -1 
"""
def pell4_min(d, epsilon):
    assert epsilon == 1 or epsilon == -1, "epsilon is neither -1 or 1"
    d_mod_4 = d & 3
    
    if d_mod_4 == 0:
        res1 = pell1_min(d/4, epsilon)
        if res1 == None: return None
        return 2*res1[0], res1[1]
    
    if d_mod_4 == 2 or d_mod_4 == 3:
        res1 = pell1_min(d, epsilon)
        if res1 == None:
            return None
        return 2 * res1[0], 2 * res1[1]

    temp = pqa(1, 2, d)
    alphas, l = temp[2], temp[-1]
    if l % 2 == 0 and epsilon == -1:
        return None

    b_i, b_im = 0, 1
    g_i, g_im = 2, -1
    pre_l = len(alphas) - l

    for i in xrange(0, l):
        alpha_i = alphas[i] if i < pre_l else alphas[pre_l + (i - pre_l) % l]
        b_i, b_im = alpha_i * b_i + b_im, b_i
        g_i, g_im = alpha_i * g_i + g_im, g_i

    # If l is odd, solution to the -4 equation.
    # If l is even, solution to the +4 equation.
    # So the only case where we have to change g and b is when
    # l is odd and epsilon is 1
    if l % 2 == 1 and epsilon == 1:
        return (g_i*g_i + b_i*b_i*d)/2, g_i * b_i

    return g_i, b_i


""" 
    Yield all the solutions for x^2 - dy^2 = epsilon, where
    epsilon can be 1 or -1 
"""
def pell1(d, epsilon):
    min_sol = pell1_min(d, epsilon)
    if min_sol == None:
        return

    t, u = min_sol
    x, y, n = t, u, 0
    while True:
        if epsilon == 1 or n % 2 == 0:
            yield x, y
        x, y, n = t*x + u*y*d, t*y + u*x, n+1


""" 
    Yield all the solutions for x^2 - dy^2 = 4*epsilon, where
    epsilon can be 1 or -1 
"""
def pell4(d, epsilon):
    min_sol = pell4_min(d, epsilon)
    if min_sol == None:
        return
    t, u = min_sol
    x, y, n = t, u, 0
    while True:
        if epsilon == 1 or n % 2 == 0:
            yield x, y
        x, y, n = (t*x + u*y*d)/2, (t*y + u*x)/2, n+1


""" 
    Finds the fundamental solutions to x^2 - dy^2 = n with a
    bounded brute force algorithm 
"""
def pell_funds_bf(d, n):
    t, u = pell1_min(d, 1)
    
    if n > 0:
        l1, l2 = 0, int(sqrt((n*(t-1))/(2.0*d)))
    else:
        l1, l2 = int(sqrt(-n/(1.0*d))), int(sqrt((-n*(t+1))/(2.0*d)))

    funds = []
    for y in xrange(l1, 1+l2):
        x = sqrt_int(abs(n + d*y*y))
        if x < 0:
            continue
        
        funds.append((x, y))
        if (x*x + d*y*y) % n != 0 or (2*x*y) % n != 0:
            funds.append((-x, y))

    return funds


""" 
    Finds the fundamental solutions to x^2 - dy^2 = n with the
    LMM algorithm.
    It turns out that the LMM algorithm scales much better than brute
    force but is slower for small n due to the overhead induced by
    factorization. 
"""
def pell_funds_lmm(d, n, n_fact = None):
    assert d > 0, "d must be positive"
    assert sqrt_int(d) == -1, "d cannot be a perfect square"
    
    funds = set([])
    if n_fact is None:
        n_fact = tools.factorize(abs(n))
    
    n_divs = tools.divisors_with_prime_factors(n_fact)
    sol, t, u, has_sol = pell1_min(d, -1), 0, 0, False
    if sol is not None:
        t, u, has_sol  = sol[0], sol[1], True
    
    for f in n_divs:
        f2 = f * f
        if not n % f2 == 0:
            continue
        
        m = n / f2
        sqrts = mod_sqrt.mod_sqrt(d, abs(m))
        if sqrts is None:
            continue
        half_m = m >> 1
        for z in sqrts:
            if z > half_m:
                z -= m
            
            p0, q0 = z, m
            a_i, a_im = 1, 0
            b_i, b_im = 0, 1
            g_i, g_im = q0, -p0
            p_i, q_i = p0, q0
            i, ir = -1, None
            sqrt_d = sqrt(d)
            while True:
                i += 1
                xi_i = (p_i + sqrt_d)/q_i
                xibar_i = (p_i - sqrt_d)/q_i
                alpha_i = int(floor(xi_i))
                a_i, a_im = alpha_i * a_i + a_im, a_i
                b_i, b_im = alpha_i * b_i + b_im, b_i
                g_i, g_im = alpha_i * g_i + g_im, g_i
                
                # Cycle begins
                if ir == None and 1 < xi_i and -1 < xibar_i and xibar_i < 0:           
                    ir, p_ir, q_ir = i, p_i, q_i
                # Cycle ends 
                if ir != None and ir != i and p_i == p_ir and q_i == q_ir:
                    break

                p_i = alpha_i * q_i - p_i
                q_i = (d - p_i * p_i) / q_i
                if q_i == 1 or q_i == -1:
                    r, s = g_i , b_i
                    if r*r - d*s*s == m:
                        funds.add((f*r, f*s))
                    elif has_sol:
                        x = f * (r*t + s*u*d)
                        y = f * (r*u + t*s)
                        funds.add((x, y))
                    break

    return funds


""" 
    Finds all solutions to x^2 - dy^2 = n where x <= max_x where
    d is a perfect square. 
"""
def pell_dn_square_d(d, n, sqrt_d, max_x, n_fact = None):
    sols = []
    div_pairs, r = [], sqrt_d
    if n == 1:
        div_pairs = [(1,1), (-1,-1)]
    elif n == -1:
        div_pairs = [(1,1), (1,-1)]
    else:
        if not n_fact:
            n_fact = tools.factorize(n)
        
        divs = tools.divisors_with_prime_factors(n_fact)
        l, r = 0, len(divs) - 1
        while l <= r:
            d1, d2 = divs[l], divs[r]
            if n > 0:
                div_pairs.append((d1, d2))
                div.pairs.append((-d1, -d2))
            else:
                div_pairs.append((d1, -d2))
                div_pairs.append((-d1, d2))

        for s, t in div_pairs:
            if (s+t) % 2 == 0 and (t-s) % (2*r) == 0:
                x = (s + t) / 2
                y = (t - s) / (2*r)
                sols.append((x,y))

    return list(sorted(sols))


""" 
    Finds all solutions to x^2 - dy^2 = n where x <= max_x 
"""
def pell_dn(d, n, max_x, n_fact = None):
    sqrt_d = sqrt_int(d)
    # If d is a perfect square, we deal with it separately
    if sqrt_d != -1:
        if n != 0:
            return pell_dn_square_d(d, n, sqrt_d, max_x, n_fact)
        else:
            # x = (+-)ry
            lim = max_x/r
            for y in range(lim+1):
                sols.append((r*y, y))
                sols.append((-r*y, y))

        return list(sorted(sols))

    
    funds = pell_funds_lmm(d, n, n_fact)

    sols = set()
    for x, y in funds:
        if abs(x) <= max_x:
            sols.add((abs(x), abs(y)))

    for t, u in pell1(d, 1):
        added = False
        
        for r, s in funds:
            x = r*t + s*u*d
            y = r*u + s*t
            if abs(x) <= max_x:
                sols.add((abs(x), abs(y)))
                added = True

        if not added:
            break

    sols = list(sols)
    return list(sorted(sols, key = lambda x: abs(x[0])))


""" 
    Finds solutions to x^2 + dy^2 = n with d, n > 0 with a 
    brute force search. :(
"""
def pell_dn_pos_d_bf(d, n):
    assert n > 0 and d > 0, "n and d have to be greater than 0"

    sols = []
    y_lim = int(math.sqrt(n / d))
    for y in range(y_lim):
        x2 = n + d*y*y
        x = sqrt_int(x2)
        if x != 1:
            sols.append((x, y))
            sols.append((-x, -y))
    return sols

""" 
    Finds solutions to x^2 + dy^2 = m 
"""
def cornacchia_dm(d, m, fact_m = None):
    if m == 1:
        return [(1, 0)]
    
    if not fact_m:
        sqrts_m = mod_sqrt.mod_sqrt(m - d, m)
    else:
        sqrts_m = mod_sqrt.mod_sqrt_pf(m - d, m, fact_m)

    if sqrts_m is None:
        return []

    sols = set()
    for s in sqrts_m:
        r0, r1 = m, s
        if r1 > (m >> 1):
            continue
        
        x = sqrt(m)
        while x < r1:
            r0, r1 = r1, tools.mod(r0, r1)

        t = m - r1*r1
        if t % d != 0:
            continue

        # We have x, backsolve for y
        s = t / d
        sqrt_s = int(sqrt(s))
        if sqrt_s * sqrt_s != s:
            continue
        sols.add((r1, sqrt_s))
            
    return list(sorted(sols, key = lambda x: abs(x[0])))


""" 
    Finds solutions to ax^2 + by^2 = m where a and m are coprime and
    m is square-free 
"""
def cornacchia_abm(a, b, m, fact_m = None):
    assert a > 0 and b > 0 and m >= a + b, "Illegal arguments given"
    assert gcd(a, b) == 1 and gcd(a, m) == 1, "Illegal arguments given"
    
    if a == 1:
        return cornacchia_dm(b, m, fact_m)
    elif b == 1:
        return cornacchia_dm(a, m, fact_m)
    elif a == m:
        return [(1, 0)]
    elif b == m:
        return [(0, 1)]
    
    a1 = mod_inverse(a, m)
    if fact_m is None:
        sqrts_m = mod_sqrt.mod_sqrt(tools.mod(m - a1*b, m), m)
    else:
        sqrts_m = mod_sqrt.mod_sqrt_pf(tools.mod(m - a1*b, m), m, fact_m)
    if sqrts_m is None:
        return []
        
    sols = set()
    half_m = m >> 1
    for r in sqrts_m:
        if r < half_m:
            continue
        u, x_lim = m, int(sqrt(m / a))
        while r >= x_lim:
            r, u = tools.mod(u, r), r
        m1 = m - a*r*r
        if m1 % b != 0:
            continue

        # We have x, backsolve for y 
        s = m1 / b
        sqrt_s = int(sqrt(s))
        if sqrt_s * sqrt_s != s:
            continue
        sols.add((r, sqrt_s))

    return list(sorted(sols, key = lambda x : abs(x[0])))
        

""" 
    Finds solutions to ax^2 + by^2 = m where a, b > 0

    TODO: This doesn't solve all cases. Fix it later. 
"""
def cornacchia(a, b, m, fact_m = None):
    if m < 0: return []
    g = gcd(a, b)
    # No solutions in this case
    if m % g != 0:
        return []
    
    a, b, m = a/g, b/g, m/g

    if fact_m is None:
        fact_m = tools.factorize(m)

    sols, sqdivs = set(), {}
    list_square_divs(1, fact_m, [], 0, sqdivs)

    for div, fact_div in sqdivs.iteritems():
        m1 = m / div
        if m1 < a + b:
            continue
        
        # Reconstruct prime factorization of divisor
        sqrt_div, m1_div = int(sqrt(div)), []
        pos0, pos1 = 0, 0
        
        # Take advatange of sorted order...similar to the
        # merge step in mergesort
        while pos1 < len(fact_div):
            if fact_m[pos0][0] < fact_div[pos1][0]:
                m1_div.append(fact_m[pos0][:])
                pos0 += 1
            else:
                if fact_m[pos0][1] > fact_div[pos1][1]:
                    m1_div.append((fact_m[pos0][0], fact_m[pos0][1] - \
                                  fact_div[pos1][1]))
                pos0 += 1; pos1 += 1

        for i in range(pos0, len(fact_m)):
            m1_div.append(fact_m[i][:])
            
        try:
            base_sols = cornacchia_abm(a, b, m1, m1_div)
            for x, y in base_sols:
                sols.add((x * sqrt_div, y * sqrt_div))
        except:
            continue

    return list(sorted(sols, key = lambda x : abs(x[0])))


""" 
    Finds solutions to ax^2 - by^2 = c where a, b > 0
"""
def solve_gen_pell(a, b, c, max_x, ac_fact = None):
    res = []
    sols = pell_dn(a*b, a*c, a*max_x, ac_fact)
    
    for x, y in sols:
        x, rem = divmod(x, a)
        if rem == 0:
            res.append((x, y))
    return res


""" 
    Finds solutions to ax^2 + by^2 = n where a > 0 and |x| <= max_x 
"""
def dioph_pell(a, b, n, max_x):
    assert a != 0 and b != 0 and n != 0, "Error: Illegal arguments"
    if a < 0:
        a, b, n = -a, -b, -n

    if b < 0:
        # There are either infinitely many or no solutions in this case
        sols = solve_gen_pell(a, -b ,n, max_x)
    else:
        # There are finitely many solutions in this case
        sols = cornacchia(a, b, n)
        sols = list(filter(lambda x : x[0] <= max_x, sols))

    return sols


##################################################
# Binary Quadratic Forms : ax^2 + bxy + cy^2 = n #
##################################################

# FIXME: Doesn't work fully
# def pqa_bqf(p0, q0, d, N, theta, df):
#     assert 0 < d, "d cannot be negative or zero"
#     assert q0 != 0, "q0 cannot be zero"
#     assert (p0*p0 - d) % q0 == 0, "p0^2 cannot be different from d modulo q0"
    
#     sqrt_d = sqrt(d)
#     assert int(sqrt_d) * int(sqrt_d) != d, "d cannot be a perfect square"

#     a_i, a_im = 1, 0
#     b_i, b_im = 0, 1
#     g_i, g_im = q0, -p0
#     p_i, q_i = p0, q0
#     i, ir = -1, None
#     p1, q1 = 0, 0
#     a0, b0 = 0, 0

#     while True:
#         i += 1
#         xi_i = (p_i + sqrt_d)/q_i
#         xibar_i = (p_i - sqrt_d)/q_i
#         alpha_i = int(floor(xi_i))
        
#         # Cycle begins
#         if ir == None and 1 < xi_i and -1 < xibar_i and xibar_i < 0:
#             ir, p_ir, q_ir = i, p_i, q_i
#         # Cycle ends
#         if ir != None and ir != i and p_i == p_ir and q_i == q_ir:
#             l = i - ir
#             if not l & 1:
#                 # Even length case - go through first period
#                 p_i, q_i, start_pow, length = p0, q0, 1, i
#                 a_i, a_im = 1, 0
#                 b_i, b_im = 0, 1
#             else:
#                 # Odd length case - go through second period
#                 p_i, q_i, start_pow, length = p_i, q_i, pow(-1 , i), i - ir
#                 a_i, b_i = a_im , b_im

#             for k in range(length):
#                 # Yay, we found a solution
#                 if k > 0 and q_i == start_pow * df:
#                     y = b_i
#                     x = y * theta + a_i * abs(N)
#                     return ((x, y))

#                 xi_i = (p_i + sqrt_d)/q_i
#                 alpha_i = int(floor(xi_i))
#                 a_i, a_im = alpha_i * a_i + a_im, a_i
#                 b_i, b_im = alpha_i * b_i + b_im, b_i
#                 p_i = alpha_i * q_i - p_i
#                 q_i = (d - p_i * p_i) / q_i
#                 start_pow *= -1
#             return None

#         a_i, a_im = alpha_i * a_i + a_im, a_i
#         b_i, b_im = alpha_i * b_i + b_im, b_i
#         g_i, g_im = alpha_i * g_i + g_im, g_i
#         p_im, q_im = p_i, q_i
#         p_i = alpha_i * q_i - p_i
#         q_i = (d - p_i * p_i) / q_i
#         if i == 1:
#             p1, q1, a0, b0 = p_i, q_i, a_i, b_i

""" 
    Finds primitive, minimal, fundamental solutions to ax^2 + bxy + cy^2 = N
    where b^2 - 4ac > 0. The minimal solution to each class comprises that with the 
    smallest positive value of "y" This can result in massive (>10^400) integers in  
    some cases. 
"""
def dioph_bqf_funds_pos_d(a, b, c, N, n_fact = []):
    assert b*b - 4*a*c > 0, "The determinant can't be negative"
    assert not tools.is_square(b*b - 4*a*c), \
            "The determinant can't be a perfect square"
    
    A, B, C = 0, 0, 0
    delta, abs_N = b*b - 4*a*c, abs(N)
    if not n_fact:
        n_fact = tools.factorize(abs_N)

    alpha, beta, gamma = 0, 0, 0
    unimodular = False
    
    # Use a unimodular transformation in this case since a^(-1) mod N
    # doesn't exist otherwise
    if gcd(a, abs_N) != 1:
        unimodular = True
        alpha, beta, gamma, delta_t = \
               find_unimodular_transform(a, b, c, N)
        A = a*alpha*alpha + b*alpha*gamma + c*gamma*gamma
        B = 2*a*alpha*beta + b * (alpha*delta_t + beta*gamma)+ \
            2*c*gamma*delta_t
        C = a*beta*beta + b*beta*delta_t + c*delta_t*delta_t
    else:
        A, B, C = a, b, c

    # Solve Ax^2 + Bx + C = 0 (mod N)
    n_4_fact, sqrts = [], []

    if abs_N > 1 and n_fact[0][0] == 2:
        n_4_fact = [(2, n_fact[0][1] + 2)] + n_fact[1:]
    elif abs_N > 1:
        n_4_fact = [(2, 2)] + n_fact[:]
         
    sqrts = sorted(filter(lambda x : x < 2 * abs_N, \
                   mod_sqrt.mod_sqrt(delta, 4 * abs_N, n_4_fact)))

    # No solutions in this case since delta has to be a square mod 4|N|.
    if not sqrts:
        return []
    
    sols = []
    for t in sqrts:
        s = t - B
        if (s & 1) == 0:
            s = s / 2
        else:
            s = tools.mod(s, 2*abs_N) / 2
        theta = tools.mod(s * mod_inverse(tools.mod(A, abs_N), \
                                          abs_N), abs_N)
        n = 2*A*theta + B
        R, S = n >> 1, A * abs_N

        # Case 1 - delta is even
        if tools.mod(delta, 2) == 0:
            
            # Omega case
            try:
                temp = pqa(-R, S, delta >> 2, True)
                #omega_sol = pqa_bqf(-R, S, delta >> 2, N, theta, N/abs_N)
            except:
                continue
            
            qs, ir, l = temp[1], temp[6], temp[-1]
            a_list, bs = temp[3], temp[4]
            if not l & 1:
                # First period
                start_j, end_j = 1, l + ir
            else:
                # Second period
                start_j, end_j = l + ir - 1, len(qs)
            d, omega_sol = N / abs_N, None
            start_pow = pow(-1, start_j)
            for j in range(start_j, end_j):
                if qs[j] == start_pow * d:
                    y = bs[j-1]
                    x = y * theta + a_list[j-1] * abs_N
                    omega_sol = (x, y)
                    break
                start_pow *= -1
            
            # No solutions for this theta, no need to go the
            # omega* case
            if not omega_sol:
              continue

            # Omega* case
            try:
                temp = pqa(R, -S, delta >> 2, True)
                #omega_star_sol = pqa_bqf(R, -S, delta >> 2, N, theta, -N/abs_N) 
            except:
                continue
            
            qs, ir, l = temp[1], temp[6], temp[-1]
            a_list, bs = temp[3], temp[4]
            if not l & 1:
                # First period
                start_j, end_j = 1, l + ir
            else:
                # Second period
                start_j, end_j = l + ir - 1, len(qs)

            d, omega_star_sol = N / abs_N, None
            start_pow = pow(-1, start_j + 1)
            for j in range(start_j, end_j):
                if qs[j] == start_pow * d:
                    y = bs[j-1]
                    x = y * theta + a_list[j-1] * abs_N
                    omega_star_sol = (x, y)
                    break
                start_pow *= -1
           
            if omega_sol[1] < omega_star_sol[1]:
                sols.append(omega_sol)
            elif omega_sol[1] > omega_star_sol[1]:
                sols.append(omega_star_sol)
            else:
                sols.append((min(omega_star_sol[0], omega_sol[0]), \
                            omega_sol[1]))

        # Case 2 = delta is odd
        else:
        # Omega case
            try:
                temp = pqa(-2*R - 1, 2*S, delta, True)
                #omega_sol = pqa_bqf(-2*R - 1, 2*S, delta, N, theta, 2*N/abs_N)
            except:
                continue

            temp_sols = []
            
            # Special case - delta = 5
            if delta == 5 and a * N < 0:
                ps, qs, l = temp[0], temp[1], temp[-1]
                a_list, bs = [1] + temp[3], [0] + temp[4]

                r = 0
                while r+l+1 < len(qs):
                    if ps[r+1] == ps[r+l+1] and \
                       qs[r+1] == qs[r+l+1]:
                        break
                    r += 1

                X = a_list[r+1] - a_list[r]
                y = bs[r+1] - bs[r]
                x = y*theta + X*abs_N
                sols.append((x, y))
                continue
            
            qs, ir, l = temp[1], temp[6], temp[-1]
            a_list, bs = temp[3], temp[4]
            if not l & 1:
                # First period
                start_j, end_j = 1, l + ir
            else:
                # Second period
                start_j, end_j = l + ir - 1, len(qs)

            d, omega_sol = 2 * (N / abs_N), None
            start_pow = pow(-1, start_j)
            for j in range(start_j, end_j):
                if qs[j] == start_pow * d:
                    y = bs[j-1]
                    x = y * theta + a_list[j-1] * abs_N
                    omega_sol = (x, y)
                    break
                start_pow *= -1
            
            # No solutions for this theta, no need to go the
            # omega* case
            if not omega_sol:
              continue
            temp_sols.append(omega_sol)
            
            # Omega* case
            try:
                temp = pqa(2*R + 1, -2*S, delta, True)
                #omega_star_sol = pqa_bqf(2*R + 1, -2*S, delta, N, theta, -2*N/abs_N)
            except:
                continue
            
            qs, ir, l = temp[1], temp[6], temp[-1]
            a_list, bs = temp[3], temp[4]                     
            if not l & 1:
                # First period
                start_j, end_j = 1, l + ir
            else:
                # Second period
                start_j, end_j = l + ir - 1, len(qs)

            d, omega_star_sol = 2 * (N / abs_N), None
            start_pow = pow(-1, start_j + 1)
            for j in range(start_j, end_j):
                if qs[j] == start_pow * d:
                    y = bs[j-1]
                    x = y * theta + a_list[j-1] * abs_N
                    omega_star_sol = (x, y)
                    break
                start_pow *= -1
            
            if omega_star_sol:
                temp_sols.append(omega_star_sol)

            if temp_sols:
                temp_sols = list(sorted(temp_sols, key = lambda x : abs(x[1])))                
                sols.append(temp_sols[0])

    # Invert the transformation if required            
    if unimodular:
        transformed_sols = []
        
        for sol in sols:
            X, Y = sol[0], sol[1]
            x = alpha*X + beta*Y
            y = gamma*X + delta_t*Y
            transformed_sols.append((x, y))
        
        sols = transformed_sols

    return sols

""" Finds fundamental solutions (generators of equivalence classes)
    of ax^2 + bxy + cy^2 = N, where d = b^2 - 4ac < 0 and a,c > 0
    Note: This is far less nasty than the previous case since each
    equivalence class has a unique reduced form and since the original
    form belongs to exactly one of them.  """
def dioph_bqf_funds_neg_d(a, b, c, N, n_fact = []):
    delta = b*b - 4*a*c
    assert delta < 0, "The determinant can't be positive"
    
    if a < 0 and c < 0:
        a, b, c, N = -a, -b, -c, -N
    
    assert a > 0 and c > 0, "Invalid arguments: a, c < 0"
    
    abs_N = abs(N)
    if not n_fact:
        n_fact = tools.factorize(abs_N)
    
    # Find the reduced form of f(x, y) = ax^2 + bxy + cy^2
    temp = find_reduced_form(a, b, c)
    a1, b1, c1 = temp[0], temp[1], temp[2]
    alpha1, beta1, gamma1, delta1 = temp[3:]
    
    # Solve n^2 = d (mod 4*N)
    n_4_fact, sqrts = [], []
    
    if abs_N > 1 and n_fact[0][0] == 2:
        n_4_fact = [(2, n_fact[0][1] + 2)] + n_fact[1:]
    elif abs_N > 1:
        n_4_fact = [(2, 2)] + n_fact[:]

    sqrts = sorted(filter(lambda x : x < (2 * abs_N), \
                          mod_sqrt.mod_sqrt(delta, 4 * abs_N, n_4_fact)))

    # No solutions in this case since delta has to be a square mod 4|N|.
    if not sqrts:
        return []

    sols = []
    for n in sqrts:
        l = (n*n - delta) // (4 * N)
        
        # Find the reduced form of g(x, y) = Nx^2 + nxy + ly^2
        # Note that g(1, 0) = N and if this is equivalent to the
        # original form, we have a fundamental solution.
        temp = find_reduced_form(N, n, l)
        a2, b2, c2 = temp[0], temp[1], temp[2]
        alpha2, beta2, gamma2, delta2 = temp[3:]
        
        # Yay, we have a solution
        if a1 == a2 and b1 == b2 and c1 == c2:
            x = alpha1 * delta2 - beta1 * gamma2
            y = gamma1 * delta2 - gamma2 * delta1
            
            if x < 0:
                x, y = -x, -y
            
            # Note that there is exactly one solution in this case
            sols.append((x, y))
            break
    
    return sols
    
""" Finds all minimal fundamental solutions to ax^2 + bxy + cy^2 = N """
def dioph_bqf_funds(a, b, c, N, fact_N = None):
    assert N != 0, "N can't equal zero"
    
    g = gcd(a, gcd(b, c))
    if tools.mod(N, g) != 0:
        return []
    
    a, b, c, N = a/g, b/g, c/g, N/g
    if fact_N is None:
        fact_N = tools.factorize(abs(N))
        
    sols, sqdivs = set(), {}
    list_square_divs(1, fact_N, [], 0, sqdivs)
    delta = b*b - 4*a*c
    
    for div, fact_div in sqdivs.iteritems():
        m1 = N / div
        # Reconstruct prime factorization of divisor
        sqrt_div, m1_div = int(sqrt(div)), []
        pos0, pos1 = 0, 0
        
        # Take advatange of sorted order...similar to the
        # merge step in mergesort
        while pos1 < len(fact_div):
            if fact_N[pos0][0] < fact_div[pos1][0]:
                m1_div.append(fact_N[pos0][:])
                pos0 += 1
            else:
                if fact_N[pos0][1] > fact_div[pos1][1]:
                    m1_div.append((fact_N[pos0][0], fact_N[pos0][1] - \
                                  fact_div[pos1][1]))
                pos0 += 1; pos1 += 1

        for i in range(pos0, len(fact_N)):
            m1_div.append(fact_N[i][:]) 

        try:
            if delta > 0:
                base_sols = dioph_bqf_funds_pos_d(a, b, c, m1, m1_div)
            elif delta < 0:
                base_sols = dioph_bqf_funds_neg_d(a, b, c, m1, m1_div)
            
            for x, y in base_sols:
                sols.add((x * sqrt_div, y * sqrt_div))
        except:
            continue
            
    return list(sorted(sols, key = lambda x : abs(x[0])))

""" 
    Finds all solutions to ax^2 + bxy + cy^2 = N where |x| <= max_x
"""
def dioph_bqf(a, b, c, N, max_x, fact_N = None):
    assert N != 0, "N can't equal zero"
    delta = b*b - 4*a*c
    assert not tools.is_square(delta if delta > 0 else 2), \
            "The determinant can't be a perfect square"
        
    g = gcd(a, gcd(b, c))
    if tools.mod(N, g) != 0:
        return []
           
    a, b, c, N = a/g, b/g, c/g, N/g
    if fact_N is None:
        fact_N = tools.factorize(abs(N))

    funds = dioph_bqf_funds(a, b, c, N, fact_N)
    sols = set([])
        
    for x, y in funds:
        if abs(x) <= max_x:
            sols.add((x, y))

    if delta > 0:
        f = pell4(delta, 1)
    else:
        f = pell_dn_pos_d_bf(-delta, 4)

    for t, u in f:
        if t == 2 and u == 0:
            continue
            
        added = False
        # If (x, y) is a fundamental solution, so is ((t-bu/2)x - cuy, 
        # aux + (t+bu/2)y) where (t, u) is a solution to t^2 - du^2 = 
        # 4.
        for x, y in funds:
            x, y = ((t - b*u) / 2) * x - c*u*y, a*u*x + ((t + b*u) / 2) * y
            while abs(x) <= max_x:
                sols.add((x, y))
                x, y = ((t - b*u) / 2) * x - c*u*y, a*u*x + ((t + b*u) / 2) * y
                added = True

        t,u = -t, -u
        for x, y in funds:
            x, y = ((t - b*u) / 2) * x - c*u*y, a*u*x + ((t + b*u) / 2) * y
            while abs(x) <= max_x:
                sols.add((x, y))
                x, y = ((t - b*u) / 2) * x - c*u*y, a*u*x + ((t + b*u) / 2) * y
                added = True


        if not added:
            break
        
    return list(sols)


###########################################################################
# Second Order Diophantine Equation : ax^2 + bxy + cy^2 + dx + ey + f = 0 #
###########################################################################


""" 
    Returns solutions to ax^2 + bxy + cy^2 + dx + ey + f = 0 where a =/= 0 
    or c =/= 0, delta = b^2 - 4ac = 0, and |x| <= max_x. 
"""
def dioph_second_order_zero_delta(a, b, c, d, e, f, max_x):
    assert a != 0 or c != 0 , "Error: Invalid arguments"
    delta = b*b - 4*a*c
    assert delta == 0, "Error: The determinant is not equal to 0"

    switched = False
    # This method requires a != 0
    if a == 0:
        a, c, d, e = c, a, e, d
        switched = True

    # Note that the equation reduces to (2ax + by + d)^2 - (2bd - 4ae)y -
    # (d^2 - 4af) = 0 which is of the form X^2 - Ay - K = 0. To solve
    # the second equation, note that X^2 = K (mod A) and you can backsolve
    # for x and y. 
    A, K = 2*b*d - 4*a*e, d*d - 4*a*f

    sols = set([])
    if A == 0:
        # K has to be a perfect square 
        if K < 0 or not tools.is_square(K):
            return []
        r = int(sqrt(K))
        # This reduces to solving 2ax + by = r - d and solving 
        # 2ax + by = -r - d
        sols1 = dioph_linear(2*a, b, r - d, max_x)
        sols2 = dioph_linear(2*a, b, -r - d, max_x)
        sols1.extend(sols2)
        return sols1
    else:
        sols, two_a, abs_A = set([]), 2*a, abs(A)
        sqrts = mod_sqrt.mod_sqrt(K, abs(A))
        
        for X in sqrts:
            y, k = (X*X - K) / A, 0

            while k <= two_a:
                if tools.mod(X - b*y - d, two_a) == 0:
                    x, temp_X = (X - b*y - d) / two_a, X
                    # Note that if X + k|A| is a solution, so is
                    # X + k|A| + 2aj|A|j > 0
                    # j >= 0
                    while x <= max_x:
                        sols.add((x, y))
                        temp_X += two_a * abs_A
                        x = (temp_X - b*y - d) / two_a

                    # j <= 0
                    while abs(x) <= max_x:
                        sols.add((x, y))
                        tempX -= two_a * abs_A
                        x = (temp_X - b*y - d) / two_a
            
                X += abs_A
                k += 1
            
        # Switch x and y if required
        if switched:
            sols = list(map(lambda x : (x[1], x[0]), sols))

        return list(sols)


""" 
    Returns solutions to ax^2 + bxy + cy^2 + dx + ey + f = 0 where a =/= 0 
    or c =/= 0, delta = b^2 - 4ac = r^2 > 0, and |x| <= max_x. 
"""
def dioph_second_order_square_delta(a, b, c, d, e, f):
    assert a != 0 or c != 0, "Error: Invalid arguments"

    delta = b*b - 4*a*c
    assert delta > 0, "Error: The determinant is not positive"
    r = sqrt_int(delta)
    assert r != -1, "Error: The determinant is not a perfect square"

    switched = False
    # This method requires a != 0
    if a == 0:
        a, c, d, e = c, a, e, d
        switched = True

    # Substituting X = 2ax + by + ry, Y = 2ax + by - ry transforms the
    # equation into BXY + DX + EY + F = 0 where B = r, D = dr - db + 2ae, 
    # E = dr + db - 2ae, F = 4afr. Note that this substitution results in
    # the "simple hyperbolic" case in the variables X and Y (refer to the
    # relevant section above)
    B, F = r, 4*a*f*r
    D, E = d*r - d*b + 2*a*e, d*r + d*b - 2*a*e

    # Note: Determining bounds on max(X) is annoying so this is a hack.
    # Substituting x = max_x leads to an extremum of y occuring at y = (-bm 
    # - e)/2c i.e. a reasonable approximation for max_X is |2a(max_x)|
    # (-b * max_x - e)/2c * (b+r). 
    if c == 0:
        transformed_sols = dioph_simple_hyperbolic(B, D, E, F)
    else:
        m_x = max_x if a > 0 else -max_x
        m_y = (-e - b*m_x) / (2 * c)
        max_X = 2*a*m_x + m_y * (b+r)
        transformed_sols = dioph_simple_hyperbolic(B, D, E, F, abs(max_X))

    # Back substitute to find potential solutions
    sols, denom_x, denom_y = [], 4*a*r, 2*r
    abs_denom_x = abs(denom_x)
    for X, Y in transformed_sols:
        numer_x = X*(r-b) + Y*(r+b)
        numer_y = X - Y

        if tools.mod(numer_x, abs_denom_x) == 0 and tools.mod(numer_y, denom_y) == 0:
            x = numer_x / denom_x
            if abs(x) <= max_x:
                y = numer_y / denom_y
                sols.add((x, y))

    # Switch x and y if required
    if switched:
        sols = list(map(lambda x : (x[1], x[0]), sols)) 

    return sols


""" 
    Transforms ax^2 + bxy + cy^2 + dx + ey + f = 0 where
    a = 0 or c = 0 to one where a != 0 and c != 0.
"""
def make_transformation_ac_non_zero(a, b, c, d, e, f, n):
    if n == 1:
        # Case 1 - a,c = 0
        # Tranform x -> X+Y, y -> X+2Y, resulting in 
        # bX^2 + 3bXY +2bY^2+ (d+e)X + (d+2e)Y + f = 0.
        a, b, c, d, e = b, 3*b, 2*b, d + e, d + 2*e
    elif n == 2:
        # Case 2a - a = 0, c != 0, b+c != 0
        # Transform x -> X, y -> X+Y, resulting in
        # (b+c)X^2 + (b+2c)XY + cY^2 + (d+e)X + eY + f = 0
        a, b, d = b + c, b + 2*c, d + e
    elif n == 3:
        # Case 2b - a = 0, c != 0, b+c = 0
        # Transform x -> X, y -> -X+Y, resulting in
        # (c-b)X^2 + (b-2c)XY + cY^2 + (d-e)X + eY + f = 0
        a, b, d = c - b, b - 2*c, d - e 
    elif n == 4:
        # Case 3a - a != 0, c = 0, a+b != 0
        # Transform x->X+Y, y->Y, resulting in
        # aX^2 +(2a+b)XY + (a+b)Y^2 + dX + (d+e)Y + f = 0
        b, c, e = 2*a + b, a + b, d + e
    else:
        # Case 3b - a != 0, c = 0, a+b = 0
        # Transform x -> -X+Y, y -> Y, resulting in
        # aX^2 + (b-2a)XY + (a-b)Y^2 + dX + (e-d)Y + f = 0
        b, c, e = b - 2*a, a - b, e - d

    return a, b, c, d, e, f


""" 
    Transforms ax^2 + bxy + cy^2 + dx + ey + f = 0 to ax^2 + cy^2 
    + dx + ey + f = 0. 
"""
def make_transformation_b_zero(a, b, c, d, e, f):
    # 2a/d = B/C
    g = tools.gcd(abs(2*a), abs(d))
    B, C = 2*a/g, d/g
    # a/B^2 = A/T
    g = tools.gcd(abs(a), B*B)
    A, T = a/g, B*B/g

    # We now have AX^2 + (cT - AC^2)Y^2 + (dT/B)X + (eT - dTC/B)Y + fT = 0
    # Now just make the coefficients integral
    g = tools.gcd(abs(d*T), abs(B))
    B_prime = abs(d*T*B) / g
    at, ct, ft = A*B_prime, B_prime*(c*T - A*C*C), f*B_prime*T
    dt = d*T*B_prime/B
    et = B_prime*e*T - C*dt

    # Construct the solution transformation matrix M such that [x, y] = M*
    # [X,Y]
    f1, f2 = fractions.Fraction(1, B), fractions.Fraction(-C, B)
    M = [[f1, f2], [0, 1]]
    return at, ct, dt, et, ft, M


""" 
    Transforms ax^2 + cy^2 + dx + ey + f = 0 to x^2 + cy^2 + dx + ey 
    + f = 0. 
"""
def make_transformation_d_zero(a, c, d, e, f):
    # 2a/d = B/C
    g = tools.gcd(abs(2*a), abs(d))
    B, C = 2*a/g, d/g
    # a/B^2 = A/T
    g = tools.gcd(abs(a), B*B)
    A, T = a/g, B*B/g

    # We now have AX^2 + (cT)Y^2 + (eT)Y + (fT - AC^2) = 0
    at, ct, et, ft = A, c*T, e*T, f*T - A*C*C

    # Construct the solution transformation matrix M and vector V such 
    # that [x, y] = M*[X,Y] + V
    f1, f2 = fractions.Fraction(1, B), fractions.Fraction(-C, B)
    M = [[f1, 0], [0, 1]]
    V = [f2, 0]
    return at, ct, et, ft, M, V


""" 
    Transforms ax^2 + cy^2 + ey + f = 0 to ax^2 + cy^2 + f = 0. 
"""
def make_transformation_e_zero(a, c, e, f):
    # 2c/e = B/C
    g = tools.gcd(abs(2*c), abs(e))
    B, C = 2*c/g, e/g
    # c/B^2 = A/T
    g = tools.gcd(abs(c), B*B)
    A, T = c/g, B*B/g

    # We now have (aT)X^2 + AY^2 + (fT - AC^2) = 0
    at, ct, ft = a*T, A, f*T - A*C*C

    # Construct the solution transformation matrix M and vector V such 
    # that [x, y] = M*[X,Y] + V
    f1, f2 = fractions.Fraction(1, B), fractions.Fraction(-C, B)
    M = [[1, 0], [0, f1]]
    V = [0, f2]
    return at, ct, ft, M, V


""" 
    Transforms ax^2 + cy^2 + ey + f = 0 to a'x^2 + c'y^2 + f' = 0. 
    with reduced coefficients if applicable. This is applicable when
    (a power of) a prime divides 'a' and 'f'. 
    
    TODO: Implement this. 
"""
def reduce_equation_prime_power(a, c, f):
    return a,c,f, [[1,0],[0,1]], [0,0]


""" 
    Transforms ax^2 + cy^2 + ey + f = 0 to a'x^2 + c'y^2 + f' = 0. 
    with reduced coefficients if applicable. This is applicable when 
    a = c (mod 4) and f = 0 (mod 4) 
"""
def reduce_equation_four_power(a, c, f):
    k = 2
    f >>= 2
    while (f & 3) == 0:
        f >>= 2
        k <<= 1

    return a, c, f, k


""" 
    Transforms ax^2 + cy^2 + f = 0 to x^2 - Dy^2 = N 
"""
def make_transformation_a_one(a, c, f):
    f1 = fractions.Fraction(1, a)
    M = [[f1, 0], [0, 1]]
    D, N = -a*c, -a*f
    return D, N, M


""" 
    Transforms ax^2 + cy^2 + f = 0 to x^2 - Dy^2 = N. This reduces the size 
    of the coefficients even further. The only case in which this doesn't reduce 
    the size of the coefficients is when both 'a' and 'c' are prime. 
"""
def make_transformation_a_one_opt(a, c, f):
    # Find the smallest r such that ra is a perfect square
    fact_a = tools.factorize(abs(a))
    r = 1
    for p,e in fact_a:
        if (e & 1) == 1:
            r *= p
    if a < 0: r = -r

    # Find the smallest s such that sc is a perfect square
    fact_c = tools.factorize(abs(c))
    s = 1
    for p,e in fact_c:
        if (e & 1) == 1:
            s *= p
    if c < 0: s = -s

    x1, x2 = abs(r*c), abs(s*a)
    if x1 < x2 or (x1 == x2 and abs(r) < abs(s)):
        sqrt_ra = int(math.sqrt(r*a))
        f1 = fractions.Fraction(1, sqrt_ra)
        M = [[f1, 0], [0, 1]]
        D, N = -r*c, -r*f
    else:
        sqrt_sc = int(math.sqrt(s*c))
        f1 = fractions.Fraction(1, sqrt_sc)
        M = [[0, f1], [1, 0]]
        D, N = -s*a, -s*f

    return D, N, M


""" 
    Returns the LCM of the denominators of the entries in M and V 
"""
def compute_L(M, V):

    """ Returns the denominator of a rational number x """
    def denom(x):
        if type(x) is fractions.Fraction:
            return x.denominator
        else:
            return 1                   

    rd, sd = denom(M[0][0]), denom(M[1][1])
    vd, wd = denom(V[0]), denom(V[1])
    g = gcd(rd, gcd(sd, gcd(td, gcd(ud, gcd(vd, wd)))))
    L = rd * ds * td * ud * vd * wd / g
    return L

"""
    Computes [x, y] = M*[X,Y] + V and returns those which are
    integral.
"""
def invert_transformation(sols, M, V):
    transformed_sols = []
    for X,Y in sols:
        XY = matrix_vector_multiply_2x2(M, [X,Y])
        x, y = XY[0] + V[0], XY[1] + V[1]
        if x.denominator == 1 and y.denominator == 1:
            transformed_sols.append((x.numerator, y.numerator))
    return transformed_sols


""" 
    Returns solutions to ax^2 + bxy + cy^2 + dx + ey + f = 0 where a =/= 0 
    or c =/= 0, delta = b^2 - 4ac = k =/= r^2 > 0, and |x| <= max_x. 
"""
def dioph_second_order_non_square_delta(a, b, c, d, e, f, max_x, opt_ac = False):
    delta = b*b - 4*a*c
    if delta > 0:
        r = sqrt_int(delta)
        assert r == -1, "Error: The determinant is a perfect square"

    # Make copies for later use
    at, bt, ct, dt, et, ft = a, b, c, d, e, f
    F = lambda a,b,c,d,e,f,X,Y: a*X*X + b*X*Y + c*Y*Y + d*X + e*Y + f

    # This method requires a =/= 0 and c =/= 0. If this isn't the case,
    # make a != 0 and c != 0 through various transformations. 
    t1 = t2 = t3 = t4 = t5 = False
    if a == 0 and c == 0:
        t1 = True
        a, b, c, d, e, f = make_transformation_ac_non_zero(a,b,c,d,e,f,1)
    elif a == 0 and c != 0:
        if b + c != 0:
            t2 = True
            a, b, c, d, e, f = make_transformation_ac_non_zero(a,b,c,d,e,f,2)
        else:
            t3 = True
            a, b, c, d, e, f = make_transformation_ac_non_zero(a,b,c,d,e,f,3) 
    elif a != 0 and c == 0:
        if a+b != 0:
            t4 = True
            a, b, c, d, e, f = make_transformation_ac_non_zero(a,b,c,d,e,f,4) 
        else:
            t5 = True
            a, b, c, d, e, f = make_transformation_ac_non_zero(a,b,c,d,e,f,5)

    
    # Transform ax^2 + bxy + cy^2 + dx + ey + f = 0 -> X^2 - DY^2 = N where
    # [x, y] = M*[X, Y] + V
    M, V = [[1, 0], [0, 1]], [0, 0]

    # Step 1 - Make b = 0 so we have ax^2 + cy^2 + dx + ey + f = 0
    if b != 0:
        a, c, d, e, f, M = make_transformation_b_zero(a,b,c,d,e,f)
    # Step 2 - Make d = 0 so we have ax^2 + cy^2 + ey + f = 0
    if d != 0:
        a, c, e, f, M2, V2 = make_transformation_d_zero(a,c,d,e,f)
        M = matrix_multiply_2x2(M2, M)
        V = V2 
    # Step 3 - Make e = 0 so we have ax^2 + cy^2 + f = 0
    if e != 0:
        a, c, f, M2, V2 = make_transformation_e_zero(a,c,e,f)
        M = matrix_multiply_2x2(M2, M)
        Vt = matrix_vector_multiply_2x2(M2, V)
        V = vector_vector_add_2x1(Vt, V2)

    # Note that if gcd(a,c) doesn't divide f, there are no solutions
    g = tools.gcd(a, c)
    if f % g != 0: return []
    a, c, f = a/g, c/g, f/g
    assert tools.gcd(a, tools.gcd(g, f)) == 1, "Someshit"

    # Step 4 - Reduce the coefficients of ax^2 + cx + f = 0 if possible
    # since equations with smaller coefficients are easier to solve in 
    # general

    # Optimization 1: A (power of a) prime dvides a and f so you can 
    # divide each of them by this prime power - NOT IMPLEMENTED
    # a, c, f, M2, V2 = reduce_equation_prime_power(a, c, f)

    # Optimization 2: a = c (mod 4) and f = 0 (mod 4). Transform to 
    # aX^2 + cY^2 + f/4 = 0 and repeat if required. 
    if (a & 3) == (c & 3):
        if (f & 3) == 0:
            a, c, f, k  = reduce_equation_four_power(a,c,f)
            M[0][0] *= k
            M[0][1] *= k
            M[1][0] *= k
            M[1][1] *= k

    # Step 5 - Make a = 1 so that we finally have x^2 - Dy^2 = N
    # TODO: It might be worthwile to factorize 'a' and reduce the
    # coefficients even further.
    if not opt_ac:
        D, N, M2 = make_transformation_a_one(a, c, f)
        M = matrix_multiply_2x2(M2, M)
    else:
        D, N, M2 = make_transformation_a_one_opt(a, c, f)
        M = matrix_multiply_2x2(M2, M)

    sols = []
    # Solve the equation x^2 - Dy^2 = N
    if D == 0:
        sqrt_N = sqrt_int(N)
        if sqrt_N != -1:
            raise Exception("There are too many solutions (x,y) with any integer y \
                            and x = (+-)" + str(sqrt_N))
        else:
            return []

    sqrt_D = sqrt_int(D)
    # If D is a perfect square
    if sqrt_D != -1:
        if N == 0:
            sols = set([])
            L = compute_L(M, V)
            for Y in range(L):
                X = k*Y
                if F(X,Y) == 0:
                    raise Exception("There are too many solutions (x,y) with x = " \
                                     + k + "y and "+ "y = " + "k" + str(L) + " + " + str(Y))
                X = -k*Y
                if F(X,Y) == 0:
                    raise Exception("There are too many solutions (x,y) with x = " \
                                     + k + "y and "+ "y = " + "k" + str(L) + " + " + str(Y))

        else:
            # There are finitely many solutions in this case
            sols = solve_gen_pell(1, D, N, max_x)
            sols = recover_solutions(sols, M, V)
    else:
        if D < 0:
            # This basically requires the BQF algorithm and there are finitely
            # many solutions in this case
            sols = pell_dn_pos_d_bf(-D, N)
            sols = recover_solutions(sols, M, V)

        elif N == 0:
            sols = V
        else:
            T, U = pell1_min(D, 1)
            L = compute_L(M, V)

            k = 0
            T_k, U_k = 1, 0
            while T_k % L != 1 and U_k % L != 0:
                T_i, U_i = (T_k * T) + (U_k * U * D), \
                               (T_k * U) + (U_k * T)
                k += 1
            
            funds = tools.pell_funds_lmm(D, N)
            for X,Y in funds:
                T_i, U_i = 1, 0
                for i in range(k):
                    X_prime = (X * T_i) + (Y * U_i * D)
                    Y_prime = (X * U_i) + (Y * T_i)
                    T_i, U_i = (T_i * T) + (U_i * U * D), \
                               (T_i * U) + (U_i * T)
                    if F(X_prime, Y_prime) == 0:
                        sols.append((X_prime, Y_prime))
        
        return list(sorted(sols, key = lambda x : x[0]))


#########
# Tests #
#########

def test():
    while True:
        args = str(input("Enter args: ")).split(" ")
        a, b, c, n = int(args[0]), int(args[1]), int(args[2]), int(args[3])
        t = time()
        x = dioph_bqf_funds(a, b, c, n)
        tim = time() - t
        print x
        print tim

# a, b, c = 12, 56, 3
# x, y = 5, 4 
# f = lambda a, b, c, x, y : a*x*x + b*x*y + c*y*y
# n = f(a, b, c, x, y)
# s = dioph_bqf(a, b, c, n, 10**7)
# print s
