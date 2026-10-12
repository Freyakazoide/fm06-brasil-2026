// Exporta o pseudo-C do "módulo Brasil" do fm.exe (FM06 6.0.2) para um arquivo.
// Uso: abrir fm.exe no CodeBrowser, rodar este script e escolher onde salvar.
//@category FM06

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.LinkedHashSet;

public class ExportBrasil extends GhidraScript {

    // Faixa onde aparecem os IDs das Séries A, B e C (0x19017, 0x1A2B7, 0x1A2B8).
    private static final long[][] RANGES = {
        {0x00BB2700L, 0x00BC0000L},
    };

    // Funções genéricas chamadas pelo módulo Brasil.
    private static final long[] EXTRAS = {
        0x00AD4220L, // construtor do sistema de ligas da nação
        0x00ACFFF0L, // init(2)
        0x00AD0050L, // adicionar divisão (id, nível, 0)
        0x00AD1410L, // finalizar(3)
        0x00ACF2F0L, // construtor base de competição
        0x00AC24F0L, // chamado no fim do construtor da Série A
        0x00BB8FD0L, // chamado pelo método [69] da Série A
    };

    @Override
    public void run() throws Exception {
        File out = askFile("Salvar pseudo-C do módulo Brasil", "Salvar");
        FunctionManager functions = currentProgram.getFunctionManager();
        LinkedHashSet<Function> selected = new LinkedHashSet<>();

        for (long[] range : RANGES) {
            AddressSet set = new AddressSet(toAddr(range[0]), toAddr(range[1]));
            for (Function f : functions.getFunctions(set, true)) {
                selected.add(f);
            }
        }
        for (long value : EXTRAS) {
            Address address = toAddr(value);
            Function f = functions.getFunctionContaining(address);
            if (f == null) {
                f = createFunction(address, null);
            }
            if (f != null) {
                selected.add(f);
            }
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        int done = 0;
        try (PrintWriter writer = new PrintWriter(new FileWriter(out))) {
            writer.println("// fm.exe " + currentProgram.getExecutableSHA256());
            for (Function f : selected) {
                if (monitor.isCancelled()) {
                    break;
                }
                monitor.setMessage("Decompilando " + (done + 1) + "/" + selected.size());
                DecompileResults result = decompiler.decompileFunction(f, 60, monitor);
                writer.println();
                writer.println("// ==== " + f.getEntryPoint() + " " + f.getName());
                if (result != null && result.decompileCompleted()) {
                    writer.println(result.getDecompiledFunction().getC());
                } else {
                    writer.println("// falhou: " + (result == null ? "sem resultado" : result.getErrorMessage()));
                }
                done++;
            }
        } finally {
            decompiler.dispose();
        }
        println("Exportadas " + done + " funções para " + out.getAbsolutePath());
    }
}
