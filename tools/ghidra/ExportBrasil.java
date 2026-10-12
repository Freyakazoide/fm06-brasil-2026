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


    // Métodos chamados só pelas vtables das classes do módulo Brasil; a
    // análise automática do Ghidra não os cria como funções.
    private static final long[] VTABLE_METHODS = {
        0x00BB2D60L, 0x00BB2D70L, 0x00BB2E90L, 0x00BB2F60L, 0x00BB3070L,
        0x00BB3210L, 0x00BB32A0L, 0x00BB3A00L, 0x00BB4440L, 0x00BB4470L,
        0x00BB4480L, 0x00BB4520L, 0x00BB45F0L, 0x00BB4A40L, 0x00BB4DA0L,
        0x00BB4E70L, 0x00BB4F50L, 0x00BB5040L, 0x00BB5090L, 0x00BB50A0L,
        0x00BB5170L, 0x00BB5180L, 0x00BB5190L, 0x00BB51A0L, 0x00BB5490L,
        0x00BB57B0L, 0x00BB73F0L, 0x00BB7400L, 0x00BB7410L, 0x00BB7420L,
        0x00BB90B0L, 0x00BB90C0L, 0x00BB9EE0L, 0x00BB9F00L, 0x00BB9F10L,
        0x00BB9F40L, 0x00BB9F50L, 0x00BB9F70L, 0x00BB9F80L, 0x00BBA010L,
        0x00BBA0D0L, 0x00BBA0F0L, 0x00BBA130L, 0x00BBA1B0L, 0x00BBA1F0L,
        0x00BBA200L, 0x00BBA230L, 0x00BBA240L, 0x00BBA260L, 0x00BBA270L,
        0x00BBA3F0L, 0x00BBA400L, 0x00BBA6A0L, 0x00BBA900L, 0x00BBA920L,
        0x00BBA940L, 0x00BBAD30L, 0x00BBB100L, 0x00BBBC90L, 0x00BBC270L,
        0x00BBCA10L, 0x00BBD750L, 0x00BBE030L, 0x00BBE990L, 0x00BBF0A0L,
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
        for (long value : VTABLE_METHODS) {
            Address address = toAddr(value);
            Function f = functions.getFunctionAt(address);
            if (f == null) {
                disassemble(address);
                f = createFunction(address, null);
            }
            if (f != null) {
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
