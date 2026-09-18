package com.acme.pedidos;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
public class PedidosController {

    @Autowired
    private PedidosService pedidosService;

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "ok");
    }

    @GetMapping("/pedidos")
    public List<String> pedidos() {
        return pedidosService.listar();
    }

    @PostMapping("/pedidos")
    public Map<String, Object> registrar(@RequestParam String pedido) {
        pedidosService.registrar(pedido);
        return Map.of("total", pedidosService.total());
    }
}
