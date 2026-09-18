package com.acme.pedidos;

import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Piloto minimo de Gradle para validar la Capa 1 parametrizada (build_tool=gradle). */
@Service
public class PedidosService {

    private final List<String> pedidos = new ArrayList<>();

    public void registrar(String pedido) {
        if (pedido == null || pedido.isBlank()) {
            throw new IllegalArgumentException("El pedido no puede estar vacio");
        }
        pedidos.add(pedido);
    }

    public List<String> listar() {
        return Collections.unmodifiableList(pedidos);
    }

    public int total() {
        return pedidos.size();
    }
}
