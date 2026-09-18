package com.acme.pedidos;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class PedidosServiceTest {

    private PedidosService service;

    @BeforeEach
    void setUp() {
        service = new PedidosService();
    }

    @Test
    void registraUnPedido() {
        service.registrar("pedido-1");
        assertEquals(1, service.total());
        assertEquals("pedido-1", service.listar().get(0));
    }

    @Test
    void registraVariosPedidos() {
        service.registrar("pedido-1");
        service.registrar("pedido-2");
        assertEquals(2, service.total());
    }

    @Test
    void rechazaPedidoVacio() {
        assertThrows(IllegalArgumentException.class, () -> service.registrar(""));
    }

    @Test
    void rechazaPedidoNulo() {
        assertThrows(IllegalArgumentException.class, () -> service.registrar(null));
    }
}
