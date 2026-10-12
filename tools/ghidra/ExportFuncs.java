// Exporta o pseudo-C das funções listadas num arquivo de texto.
// Formato do arquivo (uma entrada por linha, # comenta):
//   00B6E27F              função que contém o endereço
//   range 00B08000 00B1A000   todas as funções da faixa
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
import java.nio.file.Files;
import java.util.LinkedHashSet;

public class ExportFuncs extends GhidraScript {

    @Override
    public void run() throws Exception {
        File list = askFile("Lista de funções (tools/ghidra/export_list.txt)", "Abrir");
        File out = askFile("Salvar pseudo-C como", "Salvar");
        FunctionManager functions = currentProgram.getFunctionManager();
        LinkedHashSet<Function> selected = new LinkedHashSet<>();

        for (String raw : Files.readAllLines(list.toPath())) {
            String line = raw.split("#", 2)[0].trim();
            if (line.isEmpty()) {
                continue;
            }
            String[] parts = line.split("\\s+");
            if (parts[0].equalsIgnoreCase("range")) {
                AddressSet set = new AddressSet(toAddr(Long.parseLong(parts[1], 16)), toAddr(Long.parseLong(parts[2], 16)));
                for (Function f : functions.getFunctions(set, true)) {
                    selected.add(f);
                }
                continue;
            }
            Address address = toAddr(Long.parseLong(parts[0], 16));
            Function f = functions.getFunctionContaining(address);
            if (f == null) {
                disassemble(address);
                f = createFunction(address, null);
            }
            if (f != null) {
                selected.add(f);
            } else {
                println("Sem função em " + address);
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
