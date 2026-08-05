package br.siarrn.totem;

import br.siarrn.totem.local.BaseLocal;
import br.siarrn.totem.local.FilaOffline;
import br.siarrn.totem.rede.Aluno;
import br.siarrn.totem.rede.ApiClient;
import java.util.List;

/**
 * Verificação do totem sem abrir a interface.
 *
 * <p>Serve para dois momentos. No desenvolvimento, é o teste ponta a ponta do
 * requisito que mais importa: o totem continua registrando almoços com o
 * servidor fora do ar, e depois entrega tudo sem duplicar nada. Na escola, é o
 * que se roda para conferir se aquela máquina enxerga o servidor antes de a
 * fila se formar.
 *
 * <pre>
 *   ./gradlew verificar
 *   ./gradlew verificar --args="--servidor=http://192.168.0.10:8770 --registrar=100"
 * </pre>
 */
public final class Diagnostico {

    public static void main(String[] argumentos) {
        Config config = new Config();
        int quantosRegistrar = 0;

        for (String argumento : argumentos) {
            if (argumento.startsWith("--servidor=")) {
                config.definirServidor(argumento.substring("--servidor=".length()));
            } else if (argumento.startsWith("--registrar=")) {
                quantosRegistrar = Integer.parseInt(argumento.substring("--registrar=".length()));
            }
        }

        ApiClient api = new ApiClient(config);
        BaseLocal base = new BaseLocal();
        FilaOffline fila = new FilaOffline();

        System.out.println("SIARRN — diagnóstico do totem");
        System.out.println("  servidor configurado: " + config.servidor());

        boolean noAr = api.noAr();
        System.out.println("  servidor no ar:       " + (noAr ? "sim" : "NÃO"));

        if (noAr) {
            boolean atualizou = base.atualizar(api);
            System.out.println("  base atualizada:      " + (atualizou ? "sim" : "não"));
        }
        System.out.println("  alunos em disco:      " + base.tamanho());
        System.out.println("  fila pendente:        " + fila.pendentes());

        if (base.vazia()) {
            System.out.println("\nSem base local e sem servidor: o totem não teria nomes para mostrar.");
            System.out.println("Rode o servidor ao menos uma vez para o totem baixar a lista.");
            return;
        }

        // Prova de que a busca não depende de rede: acontece toda em memória,
        // sobre a cópia em disco.
        long inicio = System.nanoTime();
        List<Aluno> encontrados = base.buscar("sil");
        long microsegundos = (System.nanoTime() - inicio) / 1000;
        System.out.println("  busca local por 'sil': " + encontrados.size()
                + " resultados em " + microsegundos + " µs");

        if (quantosRegistrar > 0) {
            registrarEmLote(base, fila, quantosRegistrar);
        }

        if (fila.pendentes() > 0 && noAr) {
            long antes = System.currentTimeMillis();
            int enviados = fila.sincronizar(api, base);
            System.out.println("\n  sincronizados:        " + enviados
                    + " em " + (System.currentTimeMillis() - antes) + " ms");
            System.out.println("  restaram na fila:     " + fila.pendentes());
        }
    }

    /**
     * Simula a fila do almoço passando pelo totem.
     *
     * <p>O tempo medido aqui é o que a pessoa na fila sente. Se registrar cem
     * almoços demorar, nada mais no sistema importa.
     */
    private static void registrarEmLote(BaseLocal base, FilaOffline fila, int quantos) {
        List<Aluno> todos = base.amostra(quantos);
        if (todos.isEmpty()) {
            System.out.println("\nNão há alunos suficientes para o teste de carga.");
            return;
        }

        System.out.println("\nRegistrando " + quantos + " almoços...");
        long inicio = System.currentTimeMillis();
        for (int i = 0; i < quantos; i++) {
            fila.registrar(todos.get(i % todos.size()), "nome");
        }
        long total = System.currentTimeMillis() - inicio;

        System.out.println("  gravados em disco:    " + total + " ms  ("
                + String.format("%.1f", total / (double) quantos) + " ms por aluno)");
        System.out.println("  pendentes agora:      " + fila.pendentes());
    }

    private Diagnostico() {}
}
