"""
This module of SYMORO package provides symbolic
solutions for inverse geompetric problem.

The core symbolic library is sympy.
Needed modules : symoro.py, geometry.py

ECN - ARIA1 2013
"""

from heapq import heapify, heappop
from sympy import var, sin, cos, eye, atan2, sqrt, pi
from sympy import Matrix, Symbol, Expr
from symoro import Symoro, ZERO, ONE, get_max_coef
from geometry import dgm

EMPTY = var("EMPTY")

T_GENERAL = Matrix([var("s1,n1,a1,p1"), var("s2,n2,a2,p2"),
                    var("s3,n3,a3,p3"), [0, 0, 0, 1]])

#dictionary for equation type classification
eq_dict = {(1, 0, 0): 0, (0, 1, 0): 1, (1, 1, 0): 2,
           (0, 2, 0): 3, (0, 2, 1): 4}


def _paul_solve(robo, symo, nTm, n, m, known=set()):
    chain = robo.loop_chain(m, n)
    iTn = dgm(robo, symo, m, n, key='left', trig_subs=False)
    iTm = dgm(robo, symo, n, m, key='left', trig_subs=False)
#    mTi = dgm(robo, symo, m, n, key='right', trig_subs=False)
#    nTi = dgm(robo, symo, n, m, key='right', trig_subs=False)
    th_all = set()
    r_all = set()
    for i in chain:
        if i >= 0:
            if robo.sigma[i] == 0:
                th_all.add(robo.theta[i])
            if robo.sigma[i] == 1:
                r_all.add(robo.r[i])
        if isinstance(robo.gamma[i], Expr):
            known |= robo.gamma[i].atoms(Symbol)
        if isinstance(robo.alpha[i], Expr):
            known |= robo.alpha[i].atoms(Symbol)
    while True:
        repeat = False
        for i in reversed(chain):
            M_eq = iTn[(i, n)]*nTm - iTm[(i, m)]
            while True:
                found = _look_for_eq(symo, M_eq, known, th_all, r_all)
                repeat |= found
                if not found or th_all | r_all <= known:
                    break
            if th_all | r_all <= known:
                break
#        if th_all | r_all <= known:
#            break
#        for i in reversed(chain):
#            while True:
#                found = _look_for_eq(symo, M_eq, known, th_all, r_all)
#                repeat |= found
#                if not found or th_all | r_all <= known:
#                    break
#            if th_all | r_all <= known:
#                break
        if not repeat or th_all | r_all <= known:
            break
    return known


def _look_for_eq(symo, M_eq, known, th_all, r_all):
    cont_search = False
    eq_candidates = [list() for list_index in xrange(5)]
    for e1 in xrange(3):
        for e2 in xrange(4):
            if M_eq[e1, e2].has(EMPTY):
                continue
            eq = symo.unknown_sep(M_eq[e1, e2], known)
            th_vars = (eq.atoms(Symbol) & th_all) - known
            if th_vars:
                arg_sum = max(at.count_ops()-1 for at in eq.atoms(sin, cos)
                              if not at.atoms(Symbol) & known)
            else:
                arg_sum = 0
            rs_s = (eq.atoms(Symbol) & r_all) - known
            eq_features = (len(rs_s), len(th_vars), arg_sum)
            if eq_features in eq_dict:
                eq_key = eq_dict[eq_features]
                eq_pack = (eq, list(rs_s), list(th_vars))
                eq_candidates[eq_key].append(eq_pack)
    cont_search |= _try_solve_0(symo, eq_candidates[0], known)
    cont_search |= _try_solve_1(symo, eq_candidates[1], known)
    cont_search |= _try_solve_2(symo, eq_candidates[2] +
                                eq_candidates[1], known)
    cont_search |= _try_solve_3(symo, eq_candidates[3], known)
    cont_search |= _try_solve_4(symo, eq_candidates[4], known)
    return cont_search


def loop_solve(robo, symo, knowns=None):
    #TODO: rewrite; Add parallelogram detection
    q_vec = q_vec = [robo.get_q(i) for i in xrange(robo.NF)]
    loops = []
    if knowns is None:
        knowns = robo.q_active
        # set(q for i, q in enumerate(q_vec) if robo.mu[i] == 1)
    for i, j in robo.loop_terminals:
        chain = robo.loop_chain(i, j)
        knowns_ij = set(q_vec[i] for i in chain if q_vec[i] in knowns)
        unknowns_ij = set(q_vec[i] for i in chain if q_vec[i] not in knowns)
        loops.append([len(unknowns_ij), i, j, knowns_ij, unknowns_ij])
    while loops:
        heapify(loops)
        loop = heappop(loops)
        res_knowns = _paul_solve(robo, symo, eye(4), *loop[1:4])
        for l in loops:
            found = l[4] & res_knowns
            l[3] |= found
            l[4] -= found
            l[0] = len(l[4])


def igm_Paul(robo, T_ref, n):
    if isinstance(T_ref, list):
        T_ref = Matrix(4, 4, T_ref)
    symo = Symoro()
    symo.file_open(robo, 'igm')
    symo.write_params_table(robo, 'Inverse Geometrix Model for frame %s' % n)
    _paul_solve(robo, symo, T_ref, 0, n)
    symo.file_close()
    return symo


#TODO: think about smarter way of matching
def _try_solve_0(symo, eq_sys, known):
    res = False
    for eq, [r], th_names in eq_sys:
        X = get_max_coef(eq, r)
        if X != 0:
            Y = X*r - eq
            print "type 1"
            X = symo.replace(symo.CS12_simp(X), 'X', r)
            Y = symo.replace(symo.CS12_simp(Y), 'Y', r)
            symo.add_to_dict(r, Y/X)
            known.add(r)
            res = True
    return res


def _try_solve_1(symo, eq_sys, known):
    res = False
    for i in xrange(len(eq_sys)):
        eqi, rs_i, [th_i] = eq_sys[i]
        if th_i in known:
            continue
        Xi, Yi, Zi, i_ok = _get_coefs(eqi, sin(th_i), cos(th_i), th_i)
        i_ok &= sum([Xi == ZERO, Yi == ZERO, Zi == ZERO]) <= 1
        if not i_ok:
            continue
        j_ok = False
        for j in xrange(i+1, len(eq_sys)):
            eqj, rs_j, [th_j] = eq_sys[j]
            if th_i == th_j:
                Xj, Yj, Zj, j_ok = _get_coefs(eqj, sin(th_j), cos(th_j), th_i)
                j_ok &= (Xi*Yj != Xj*Yi)
                if j_ok:
                    break
        if j_ok:
            symo.write_line("# Solving type 3")
            _solve_type_3(symo, Xi, Yi, -Zi, Xj, Yj, -Zj, th_i)
        else:
            symo.write_line("# Solving type 2")
            _solve_type_2(symo, Xi, Yi, -Zi, th_i)
        known.add(th_i)
        res = True
    return res


def _try_solve_2(symo, eq_sys, known):
    if all(len(rs) == 0 for eq, rs, ths in eq_sys):
        return False
    for i in xrange(len(eq_sys)):
        all_ok = False
        for j in xrange(len(eq_sys)):
            eqj, rs_j, ths_j = eq_sys[j]
            eqi, rs_i, ths_i = eq_sys[i]
            if i == j or set(ths_i) != set(ths_j) or set(rs_j) != set(rs_i):
                continue
            th = ths_i[0]
            C, S = cos(th), sin(th)
            r = rs_i[0]
            X1, Y1, Z1, i_ok = _get_coefs(eqi, S, r, th, r)
            X2, Y2, Z2, j_ok = _get_coefs(eqj, C, r, th, r)
            all_ok = j_ok and i_ok and not eqi.has(C) and not eqj.has(S)
            if all_ok:
                eq_type = 5
                break
            X1, Y1, Z1, i_ok = _get_coefs(eqi, S, C, th, r)
            X2, Y2, Z2, j_ok = _get_coefs(eqj, C, S, th, r)
            i_ok &= X1.has(r) and not Z1.has(r) and Y1 == ZERO
            j_ok &= X2.has(r) and not Z2.has(r) and Y2 == ZERO
            all_ok = j_ok and i_ok
            if all_ok:
                eq_type = 4
                X1 /= r
                X2 /= r
                break
            else:
                eq_type = -1
        if not all_ok or eq_type == -1:
            continue
        symo.write_line("# Solving type %s" % eq_type)
        if eq_type == 4:
            _solve_type_4(symo, X1, Y1, X2, Y2, th, r)
        else:
            _solve_type_5(symo, X1, Y1, Z1, X2, Y2, Z2, th, r)
        known |= {th, r}
        return True
    return False


def _match_coef(A1, A2, B1, B2):
    return A1 == A2 and B1 == B2 or A1 == -A2 and B1 == -B2


def _try_solve_3(symo, eq_sys, known):
    for i in xrange(len(eq_sys)):
        all_ok = False
        for j in xrange(len(eq_sys)):
            eqj, rs_j, ths_i = eq_sys[j]
            eqi, rs_i, ths_j = eq_sys[i]
            if i == j or set(ths_i) != set(ths_j):
                continue
            th1 = ths_i[0]
            th2 = ths_i[1]
            C1, S1 = cos(th1), sin(th1)
            C2, S2 = cos(th2), sin(th2)
            X1, Y1, ZW1, i_ok = _get_coefs(eqi, C1, S1, th1)
            X2, Y2, ZW2, j_ok = _get_coefs(eqj, S1, C1, th1)
            Y2 = -Y2
            V1, W1, Z1, iw_ok = _get_coefs(ZW1, C2, S2, th1, th2)
            V2, W2, Z2, jw_ok = _get_coefs(ZW2, S2, C2, th1, th2)
            W2 = -W2
            all_ok = j_ok and i_ok and jw_ok and iw_ok
            all_ok &= _check_const((X1, Y1), th2)
            if X1 == 0 or Y1 == 0:
                X1, Y1, V1, W1 = V1, W1, X1, Y1
                X2, Y2, V2, W2 = V2, W2, X2, Y2
                th1, th2 = th2, th1
            all_ok &= _match_coef(X1, X2, Y1, Y2)
            all_ok &= _match_coef(V1, V2, W1, W2)
            eps = 1
            if X1 == X2 and Y1 == Y2:
                if W1 == -W2 and V1 == -V2:
                    eps = -1
            else:
                if W1 == W2 and V1 == V2:
                    eps = -1
                Z2 = -Z2
            for a in (X1, X2, Y1, Y2):
                all_ok &= not a.has(C2)
                all_ok &= not a.has(S2)
            if all_ok:
                break
        if not all_ok:
            continue
        symo.write_line("# Solving type 6, 7")
        _solve_type_7(symo, V1, W1, -X1, -Y1, -Z1, -Z2, eps, th1, th2)
        known |= {th1, th2}
        return True
    return False


#TODO: make it with itertool
def _try_solve_4(symo, eq_sys, known):
    res = False
    for i in xrange(len(eq_sys)):
        all_ok = False
        for j in xrange(len(eq_sys)):
            eqj, rs_j, ths_i = eq_sys[j]
            eqi, rs_i, ths_j = eq_sys[i]
            if i == j or set(ths_i) != set(ths_j):
                continue
            th12 = ths_i[0] + ths_i[1]
            if eqi.has(sin(ths_i[0])) or eqi.has(cos(ths_i[0])):
                th1 = ths_i[0]
                th2 = ths_i[1]
            else:
                th1 = ths_i[1]
                th2 = ths_i[0]
            C1, S1 = cos(th1), sin(th1)
            C12, S12 = cos(th12), sin(th12)
            X1, Y1, Z1, i_ok = _get_coefs(eqi, C1, C12, th1, th2)
            X2, Y2, Z2, j_ok = _get_coefs(eqj, S1, S12, th1, th2)
            all_ok = (X1*Y2 == Y1*X2 and i_ok and j_ok)
            all_ok &= not eqi.has(S1) and not eqi.has(S12)
            all_ok &= not eqj.has(C1) and not eqj.has(C12)
            if all_ok:
                break
        if not all_ok:
            continue
        symo.write_line("# Solving type 8")
        _solve_type_8(symo, X1, Y1, Z1, Z2, th1, th2)
        known |= {th1, th2}
        res = True
    return res


def _solve_type_2(symo, X, Y, Z, th):
    """Solution for the equation:
    X*S + Y*C = Z
    """
    symo.write_line("# X*sin({0}) + Y*cos({0}) = Z".format(th))
    X = symo.replace(symo.CS12_simp(X), 'X', th)
    Y = symo.replace(symo.CS12_simp(Y), 'Y', th)
    Z = symo.replace(symo.CS12_simp(Z), 'Z', th)
    YPS = var('YPS'+str(th))
    if X == ZERO and Y != ZERO:
        C = symo.replace(Z/Y, 'C', th)
        symo.add_to_dict(YPS, (ONE, - ONE))
        symo.add_to_dict(th, atan2(YPS*sqrt(1-C**2), C))
    elif X != ZERO and Y == ZERO:
        S = symo.replace(Z/X, 'S', th)
        symo.add_to_dict(YPS, (ONE, - ONE))
        symo.add_to_dict(th, atan2(S, YPS*sqrt(1-S**2)))
    elif Z == ZERO:
        symo.add_to_dict(YPS, (ONE, ZERO))
        symo.add_to_dict(th, atan2(-Y, X) + YPS*pi)
    else:
        B = symo.replace(X**2 + Y**2, 'B', th)
        D = symo.replace(B - Z**2, 'D', th)
        symo.add_to_dict(YPS, (ONE, - ONE))
        S = symo.replace((X*Z + YPS * Y * sqrt(D))/B, 'S', th)
        C = symo.replace((Y*Z - YPS * X * sqrt(D))/B, 'C', th)
        symo.add_to_dict(th, atan2(S, C))


def _solve_type_3(symo, X1, Y1, Z1, X2, Y2, Z2, th):
    """Solution for the system:
    X1*S + Y1*C = Z1
    X2*S + Y2*C = Z2
    """
    symo.write_line("# X1*sin({0}) + Y1*cos({0}) = Z1".format(th))
    symo.write_line("# X2*sin({0}) + Y2*cos({0}) = Z2".format(th))
    X1 = symo.replace(symo.CS12_simp(X1), 'X1', th)
    Y1 = symo.replace(symo.CS12_simp(Y1), 'Y1', th)
    Z1 = symo.replace(symo.CS12_simp(Z1), 'Z1', th)
    X2 = symo.replace(symo.CS12_simp(X2), 'X2', th)
    Y2 = symo.replace(symo.CS12_simp(Y2), 'Y2', th)
    Z2 = symo.replace(symo.CS12_simp(Z2), 'Z2', th)
    if X1 == ZERO and Y2 == ZERO:
        symo.add_to_dict(th, atan2(Z2/X2, Z1/Y1))
    elif X2 == ZERO and Y1 == ZERO:
        symo.add_to_dict(th, atan2(Z1/X1, Z2/Y2))
    else:
        D = symo.replace(X1*Y2-X2*Y1, 'D', th)
        C = symo.replace((Z2*X1 - Z1*X2)/D, 'C', th)
        S = symo.replace((Z1*Y2 - Z2*Y1)/D, 'S', th)
        symo.add_to_dict(th, atan2(S, C))


def _solve_type_4(symo, X1, Y1, X2, Y2, th, r):
    """Solution for the system:
    X1*S*r = Y1
    X2*C*r = Y2
    """
    symo.write_line("# X1*sin({0})*{1} = Y1".format(th, r))
    symo.write_line("# X2*cos({0})*{1} = Y2".format(th, r))
    X1 = symo.replace(symo.CS12_simp(X1), 'X1', th)
    Y1 = symo.replace(symo.CS12_simp(Y1), 'Y1', th)
    X2 = symo.replace(symo.CS12_simp(X2), 'X2', th)
    Y2 = symo.replace(symo.CS12_simp(Y2), 'Y2', th)
    YPS = var('YPS' + r)
    symo.add_to_dict(YPS, (ONE, - ONE))
    symo.add_to_dict(r, YPS*sqrt((Y1/X1)**2 + (Y2/X2)**2))
    symo.add_to_dict(th, atan2(Y1/(X1*r), Y2/(X2*r)))


def _solve_type_5(symo, X1, Y1, Z1, X2, Y2, Z2, th, r):
    """Solution for the system:
    X1*S = Y1 + Z1*r
    X2*C = Y2 + Z2*r
    """
    symo.write_line("# X1*sin({0}) = Y1 + Z1*{1}".format(th, r))
    symo.write_line("# X2*cos({0}) = Y2 + Z2*{1}".format(th, r))
    X1 = symo.replace(symo.CS12_simp(X1), 'X1', th)
    Y1 = symo.replace(symo.CS12_simp(Y1), 'Y1', th)
    Z1 = symo.replace(symo.CS12_simp(Z1), 'Z1', th)
    X2 = symo.replace(symo.CS12_simp(X2), 'X2', th)
    Y2 = symo.replace(symo.CS12_simp(Y2), 'Y2', th)
    Z2 = symo.replace(symo.CS12_simp(Z2), 'Z2', th)
    V1 = symo.replace(Y1/X1, 'V1', r)
    W1 = symo.replace(Z1/X1, 'W1', r)
    V2 = symo.replace(Y2/X2, 'V2', r)
    W2 = symo.replace(Z2/X2, 'W2', r)
    _solve_square(W1**2 + W2**2, 2*(V1*W1 + V2*W2), V1**2 + V2**2, r)
    _solve_type_3(X1, ZERO, Y1 + Z1*r, ZERO, X2, Y2 + Z2*r)


def _solve_type_7(symo, V, W, X, Y, Z1, Z2, eps, th_i, th_j):
    """Solution for the system:
    V1*Cj + W1*Sj = X*Ci + Y*Si + Z1
    eps*(V2*Sj - W2*Cj) = X*Si - Y*Ci + Z2
    """
    s = "# V*cos({0}) + W*sin({0}) = X*cos({1}) + Y*sin({1}) + Z1"
    symo.write_line(s.format(th_j, th_i))
    s = "# eps*(V*sin({0}) - W*cos({0})) = X*sin({1}) - Y*cos({1}) + Z2"
    symo.write_line(s.format(th_j, th_i))
    V = symo.replace(symo.CS12_simp(V), 'V', th_i)
    W = symo.replace(symo.CS12_simp(W), 'W', th_i)
    X = symo.replace(symo.CS12_simp(X), 'X', th_i)
    Y = symo.replace(symo.CS12_simp(Y), 'Y', th_i)
    Z1 = symo.replace(symo.CS12_simp(Z1), 'Z1', th_i)
    Z2 = symo.replace(symo.CS12_simp(Z2), 'Z2', th_i)
    B1 = symo.replace(2*(Z1*Y + Z2*X), 'B1', th_i)
    B2 = symo.replace(2*(Z1*X - Z2*Y), 'B2', th_i)
    B3 = symo.replace(V**2 + W**2 - X**2 - Y**2 - Z1**2 - Z2**2, 'B3', th_i)
    _solve_type_2(symo, B1, B2, B3, th_i)
    Zi1 = symo.replace(X*cos(th_i) + Y*sin(th_i) + Z1, 'Zi1', th_j)
    Zi2 = symo.replace(X*sin(th_i) - Y*cos(th_i) + Z2, 'Zi2', th_j)
    _solve_type_3(symo, W, V, Zi1, eps*V, -eps*W, Zi2, th_j)
#    print_eq(symo, "V1", "X*sin({0}) + Y*cos({0}) + Z1".format(th_i))
#    print_eq(symo, "V2", "X*cos({0}) - Y*sin({0}) + Z2".format(th_i))
#    print_eq(symo, "C", "(V1 - V2)/(2*W2)")
#    print_eq(symo, "S", "(V1 + V2)/(2*W1)")
#    print_eq(symo, th_j, "atan2(S, C)")


def _solve_type_8(symo, X, Y, Z1, Z2, th_i, th_j):
    """Solution for the system:
    X*Ci + Y*Cij = Z1
    X*Si + Y*Sij = Z2
    """
    symo.write_line("# X*cos({0}) + Y*cos({0} + {1}) = Z1".format(th_i, th_j))
    symo.write_line("# X*sin({0}) + Y*sin({0} + {1}) = Z2".format(th_i, th_j))
    X = symo.replace(symo.CS12_simp(X), 'X', th_j)
    Y = symo.replace(symo.CS12_simp(Y), 'Y', th_j)
    Z1 = symo.replace(symo.CS12_simp(Z1), 'Z1', th_j)
    Z2 = symo.replace(symo.CS12_simp(Z2), 'Z2', th_j)
    Cj = symo.replace((Z1**2 + Z2**2 - X**2 - Y**2) / (2*X*Y), 'C', th_j)
    YPS = var('YPS%s' % th_j)
    symo.add_to_dict(YPS, (ONE, - ONE))
    symo.add_to_dict(th_j, atan2(YPS*sqrt(1 - Cj**2), Cj))
    Q1 = symo.replace(X + Y*cos(th_j), 'Q1', th_i)
    Q2 = symo.replace(X + Y*sin(th_j), 'Q2', th_i)
    Den = symo.replace(Q1**2+Q2**2, 'Den', th_i)
    Si = symo.replace((Q1*Z2 - Q2*Z1)/Den, 'S', th_i)
    Ci = symo.replace((Q1*Z1 + Q2*Z2)/Den, 'C', th_i)
    symo.add_to_dict(th_i, atan2(Si, Ci))


def _solve_square(symo, A, B, C, x):
    """ solution for the equation:
    A*x**2 + B*x + C = 0
    """
    A = symo.replace(A, 'A', x)
    B = symo.replace(B, 'B', x)
    C = symo.replace(C, 'C', x)
    Delta = symo.repalce(B**2 - 4*A*C, 'Delta', x)
    YPS = var('YPS' + x)
    symo.add_to_dict(YPS, (ONE, - ONE))
    symo.add_to_dict(x, (-B + YPS*sqrt(Delta))/(2*A))


def _is_parallelogram(robo, i, j):
    k = robo.common_root(i, j)
    chi = robo.chain(i,k)
    chj = robo.chain(j,k)


def _check_const(consts, *xs):
    is_ok = True
    for coef in consts:
        for x in xs:
            is_ok &= not coef.has(x)
    return is_ok


def _get_coefs(eq, A1, A2, *xs):
    eqe = eq.expand()
    X = get_max_coef(eqe, A1)
    eqe = eqe.xreplace({A1: ZERO})
    Y = get_max_coef(eqe, A2)
    Z = eqe.xreplace({A2: ZERO})
#    is_ok = not X.has(A2) and not X.has(A1) and not Y.has(A2)
    is_ok = True
    is_ok &= _check_const((X, Y, Z), *xs)
#    if is_ok != is_ok2:
#        print 'GET COEF333333333333333333333333333333333333333333333"'
#        print X, Y, Z, is_ok
#        print eq, 'i', A1, 'i', A2
#        print xs
    return X, Y, Z, is_ok
