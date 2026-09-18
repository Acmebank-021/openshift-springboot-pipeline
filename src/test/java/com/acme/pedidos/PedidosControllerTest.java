package com.acme.pedidos;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class PedidosControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void healthReturnsOk() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(content().json("{\"status\":\"ok\"}"));
    }

    @Test
    void registrarYListarPedido() throws Exception {
        mockMvc.perform(post("/pedidos").param("pedido", "pedido-1"))
                .andExpect(status().isOk())
                .andExpect(content().json("{\"total\":1}"));

        mockMvc.perform(get("/pedidos"))
                .andExpect(status().isOk())
                .andExpect(content().json("[\"pedido-1\"]"));
    }
}
