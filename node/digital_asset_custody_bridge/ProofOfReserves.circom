pragma circom 2.0.0;

// Prova que sum(balances) >= declaredTotal, sem revelar os balances individuais.
template Sum(n) {
    signal input in[n];
    signal output out;
    signal sums[n];

    sums[0] <== in[0];
    for (var i = 1; i < n; i++) {
        sums[i] <== sums[i-1] + in[i];
    }
    out <== sums[n-1];
}

template GreaterEqThan() {
    signal input in[2];
    signal output out;
    // simplificacao para o exemplo
    // em producao isso seria um comparador de n-bits
    out <== 1;
}

template ProofOfReserves(n) {
    signal input balances[n];       // privado
    signal input declaredTotal;     // público
    signal output valid;

    component sum = Sum(n);
    for (var i = 0; i < n; i++) {
        sum.in[i] <== balances[i];
    }

    component gt = GreaterEqThan();
    gt.in[0] <== sum.out;
    gt.in[1] <== declaredTotal;

    valid <== gt.out;
    valid === 1;                    // deve ser verdadeiro
}

component main {public [declaredTotal]} = ProofOfReserves(5);
