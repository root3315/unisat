/**
  ******************************************************************************
  *  UniSat — STM32F446RETx startup code
  *
  *  Responsibilities (Cortex-M4, GCC syntax)
  *    1. Publish the interrupt vector table into section .isr_vector so the
  *       linker places it at 0x08000000 (see STM32F446RETx_FLASH.ld).
  *    2. On reset:
  *         * Load MSP from the first vector-table slot.
  *         * Copy .data from its load-address in flash (_sidata) to its
  *           run-address in SRAM (_sdata..._edata).
  *         * Zero-fill .bss (_sbss..._ebss).
  *         * Call SystemInit (CMSIS — configures FPU, vector offset).
  *         * Call __libc_init_array so global C++ ctors and __attribute__
  *           ((constructor)) functions run.
  *         * Branch to main().  If main ever returns, we trap in an
  *           infinite loop so a mis-configured build fails visibly in a
  *           debugger instead of returning into random flash.
  *    3. Provide a weak Default_Handler for every IRQ so drivers can
  *       override only the ones they need. All other IRQs spin in place,
  *       which keeps HardFault from firing on unexpected peripherals and
  *       preserves registers for post-mortem inspection via SWD.
  *
  *  Cortex-M4 exception table layout (first 16 slots) and the STM32F446
  *  IRQn list (slots 16..112) are from RM0390 rev 5, table 38.
  ******************************************************************************
  */

    .syntax unified
    .cpu cortex-m4
    .fpu softvfp
    .thumb

/* Symbols exported by the linker script */
.global  g_pfnVectors
.global  Default_Handler

/* From STM32F446RETx_FLASH.ld */
.word    _sidata
.word    _sdata
.word    _edata
.word    _sbss
.word    _ebss

/*
 * =============================================================================
 *  Reset handler — runs from flash on power-on / NVIC reset.
 *
 *  Register usage:
 *    r0  scratch (source / destination pointers, word value)
 *    r1  destination pointer
 *    r2  end pointer
 *    r3  LR backup across bl calls we don't care about returning to
 * =============================================================================
 */
    .section  .text.Reset_Handler
    .weak     Reset_Handler
    .type     Reset_Handler, %function
Reset_Handler:
    ldr   sp, =_estack        /* defensive — HW already loaded MSP from VT */

    /* ------------------------------------------------------------
     * Copy .data initialiser values from flash to SRAM.
     *   src  = _sidata  (flash)
     *   dst  = _sdata  ..  _edata  (RAM)
     * ------------------------------------------------------------ */
    ldr   r0, =_sdata
    ldr   r1, =_edata
    ldr   r2, =_sidata
    movs  r3, #0
    b     LoopCopyDataInit

CopyDataInit:
    ldr   r4, [r2, r3]
    str   r4, [r0, r3]
    adds  r3, r3, #4

LoopCopyDataInit:
    adds  r4, r0, r3
    cmp   r4, r1
    bcc   CopyDataInit

    /* ------------------------------------------------------------
     * Zero-fill .bss.
     * ------------------------------------------------------------ */
    ldr   r2, =_sbss
    ldr   r4, =_ebss
    movs  r3, #0
    b     LoopFillZerobss

FillZerobss:
    str   r3, [r2]
    adds  r2, r2, #4

LoopFillZerobss:
    cmp   r2, r4
    bcc   FillZerobss

    /* ------------------------------------------------------------
     * System & libc init, then jump to main.
     *   SystemInit is provided by CMSIS system_stm32f4xx.c (weak;
     *   UniSat ships its own in Core/Src/system_stm32f4xx.c).
     * ------------------------------------------------------------ */
    bl    SystemInit
    bl    __libc_init_array
    bl    main

    /* main() should never return; if it does, trap so the failure
     * is visible under SWD. */
HangForever:
    b     HangForever
    .size Reset_Handler, .-Reset_Handler


/*
 * =============================================================================
 *  Default IRQ handler — weak fallback for every slot below.
 *  A peripheral driver that provides its own handler with the matching
 *  symbol name transparently overrides this default.
 * =============================================================================
 */
    .section  .text.Default_Handler, "ax", %progbits
Default_Handler:
Infinite_Loop:
    b    Infinite_Loop
    .size Default_Handler, .-Default_Handler


/*
 * =============================================================================
 *  Interrupt vector table — placed at flash base by the linker.
 * =============================================================================
 */
    .section  .isr_vector, "a", %progbits
    .type     g_pfnVectors, %object
    .size     g_pfnVectors, .-g_pfnVectors

g_pfnVectors:
    .word  _estack                         /*  0 Initial MSP              */
    .word  Reset_Handler                   /*  1 Reset                    */
    .word  NMI_Handler                     /*  2 NMI                      */
    .word  HardFault_Handler               /*  3 Hard fault               */
    .word  MemManage_Handler               /*  4 MPU fault                */
    .word  BusFault_Handler                /*  5 Bus fault                */
    .word  UsageFault_Handler              /*  6 Usage fault              */
    .word  0                               /*  7 Reserved                 */
    .word  0                               /*  8 Reserved                 */
    .word  0                               /*  9 Reserved                 */
    .word  0                               /* 10 Reserved                 */
    .word  SVC_Handler                     /* 11 SVCall                   */
    .word  DebugMon_Handler                /* 12 Debug monitor            */
    .word  0                               /* 13 Reserved                 */
    .word  PendSV_Handler                  /* 14 PendSV (FreeRTOS ctx-sw) */
    .word  SysTick_Handler                 /* 15 SysTick                  */

    /* ---- STM32F446 peripheral IRQs (RM0390 §10, table 38) ---- */
    .word  WWDG_IRQHandler                 /*  0 Window watchdog          */
    .word  PVD_IRQHandler                  /*  1 PVD through EXTI         */
    .word  TAMP_STAMP_IRQHandler           /*  2 Tamper + timestamp       */
    .word  RTC_WKUP_IRQHandler             /*  3 RTC wake-up              */
    .word  FLASH_IRQHandler                /*  4 Flash global             */
    .word  RCC_IRQHandler                  /*  5 RCC global               */
    .word  EXTI0_IRQHandler                /*  6 EXTI line 0              */
    .word  EXTI1_IRQHandler                /*  7 EXTI line 1              */
    .word  EXTI2_IRQHandler                /*  8 EXTI line 2              */
    .word  EXTI3_IRQHandler                /*  9 EXTI line 3              */
    .word  EXTI4_IRQHandler                /* 10 EXTI line 4              */
    .word  DMA1_Stream0_IRQHandler         /* 11 DMA1 stream 0            */
    .word  DMA1_Stream1_IRQHandler         /* 12 DMA1 stream 1            */
    .word  DMA1_Stream2_IRQHandler         /* 13 DMA1 stream 2            */
    .word  DMA1_Stream3_IRQHandler         /* 14 DMA1 stream 3            */
    .word  DMA1_Stream4_IRQHandler         /* 15 DMA1 stream 4            */
    .word  DMA1_Stream5_IRQHandler         /* 16 DMA1 stream 5            */
    .word  DMA1_Stream6_IRQHandler         /* 17 DMA1 stream 6            */
    .word  ADC_IRQHandler                  /* 18 ADC1/2/3 global          */
    .word  CAN1_TX_IRQHandler              /* 19 CAN1 TX                  */
    .word  CAN1_RX0_IRQHandler             /* 20 CAN1 RX0                 */
    .word  CAN1_RX1_IRQHandler             /* 21 CAN1 RX1                 */
    .word  CAN1_SCE_IRQHandler             /* 22 CAN1 SCE                 */
    .word  EXTI9_5_IRQHandler              /* 23 EXTI lines 9..5          */
    .word  TIM1_BRK_TIM9_IRQHandler        /* 24 TIM1 break + TIM9        */
    .word  TIM1_UP_TIM10_IRQHandler        /* 25 TIM1 update + TIM10      */
    .word  TIM1_TRG_COM_TIM11_IRQHandler   /* 26 TIM1 trigger + TIM11     */
    .word  TIM1_CC_IRQHandler              /* 27 TIM1 capture/compare     */
    .word  TIM2_IRQHandler                 /* 28 TIM2                     */
    .word  TIM3_IRQHandler                 /* 29 TIM3                     */
    .word  TIM4_IRQHandler                 /* 30 TIM4                     */
    .word  I2C1_EV_IRQHandler              /* 31 I2C1 event               */
    .word  I2C1_ER_IRQHandler              /* 32 I2C1 error               */
    .word  I2C2_EV_IRQHandler              /* 33 I2C2 event               */
    .word  I2C2_ER_IRQHandler              /* 34 I2C2 error               */
    .word  SPI1_IRQHandler                 /* 35 SPI1                     */
    .word  SPI2_IRQHandler                 /* 36 SPI2                     */
    .word  USART1_IRQHandler               /* 37 USART1                   */
    .word  USART2_IRQHandler               /* 38 USART2                   */
    .word  USART3_IRQHandler               /* 39 USART3                   */
    .word  EXTI15_10_IRQHandler            /* 40 EXTI lines 15..10        */
    .word  RTC_Alarm_IRQHandler            /* 41 RTC alarms               */
    .word  OTG_FS_WKUP_IRQHandler          /* 42 USB OTG FS wake-up       */
    .word  TIM8_BRK_TIM12_IRQHandler       /* 43 TIM8 break + TIM12       */
    .word  TIM8_UP_TIM13_IRQHandler        /* 44 TIM8 update + TIM13      */
    .word  TIM8_TRG_COM_TIM14_IRQHandler   /* 45 TIM8 trigger + TIM14     */
    .word  TIM8_CC_IRQHandler              /* 46 TIM8 capture/compare     */
    .word  DMA1_Stream7_IRQHandler         /* 47 DMA1 stream 7            */
    .word  FMC_IRQHandler                  /* 48 FMC                      */
    .word  SDIO_IRQHandler                 /* 49 SDIO                     */
    .word  TIM5_IRQHandler                 /* 50 TIM5                     */
    .word  SPI3_IRQHandler                 /* 51 SPI3                     */
    .word  UART4_IRQHandler                /* 52 UART4                    */
    .word  UART5_IRQHandler                /* 53 UART5                    */
    .word  TIM6_DAC_IRQHandler             /* 54 TIM6 + DAC1/DAC2         */
    .word  TIM7_IRQHandler                 /* 55 TIM7                     */
    .word  DMA2_Stream0_IRQHandler         /* 56 DMA2 stream 0            */
    .word  DMA2_Stream1_IRQHandler         /* 57 DMA2 stream 1            */
    .word  DMA2_Stream2_IRQHandler         /* 58 DMA2 stream 2            */
    .word  DMA2_Stream3_IRQHandler         /* 59 DMA2 stream 3            */
    .word  DMA2_Stream4_IRQHandler         /* 60 DMA2 stream 4            */
    .word  0                               /* 61 Reserved                 */
    .word  0                               /* 62 Reserved                 */
    .word  CAN2_TX_IRQHandler              /* 63 CAN2 TX                  */
    .word  CAN2_RX0_IRQHandler             /* 64 CAN2 RX0                 */
    .word  CAN2_RX1_IRQHandler             /* 65 CAN2 RX1                 */
    .word  CAN2_SCE_IRQHandler             /* 66 CAN2 SCE                 */
    .word  OTG_FS_IRQHandler               /* 67 USB OTG FS               */
    .word  DMA2_Stream5_IRQHandler         /* 68 DMA2 stream 5            */
    .word  DMA2_Stream6_IRQHandler         /* 69 DMA2 stream 6            */
    .word  DMA2_Stream7_IRQHandler         /* 70 DMA2 stream 7            */
    .word  USART6_IRQHandler               /* 71 USART6                   */
    .word  I2C3_EV_IRQHandler              /* 72 I2C3 event               */
    .word  I2C3_ER_IRQHandler              /* 73 I2C3 error               */
    .word  OTG_HS_EP1_OUT_IRQHandler       /* 74 USB HS EP1 OUT           */
    .word  OTG_HS_EP1_IN_IRQHandler        /* 75 USB HS EP1 IN            */
    .word  OTG_HS_WKUP_IRQHandler          /* 76 USB HS wake-up           */
    .word  OTG_HS_IRQHandler               /* 77 USB HS                   */
    .word  DCMI_IRQHandler                 /* 78 DCMI                     */
    .word  0                               /* 79 Reserved                 */
    .word  0                               /* 80 Reserved                 */
    .word  FPU_IRQHandler                  /* 81 FPU                      */
    .word  0                               /* 82 Reserved                 */
    .word  0                               /* 83 Reserved                 */
    .word  SPI4_IRQHandler                 /* 84 SPI4                     */
    .word  0                               /* 85 Reserved                 */
    .word  0                               /* 86 Reserved                 */
    .word  SAI1_IRQHandler                 /* 87 SAI1                     */
    .word  0                               /* 88 Reserved                 */
    .word  0                               /* 89 Reserved                 */
    .word  0                               /* 90 Reserved                 */
    .word  SAI2_IRQHandler                 /* 91 SAI2                     */
    .word  QUADSPI_IRQHandler              /* 92 QuadSPI                  */
    .word  CEC_IRQHandler                  /* 93 HDMI-CEC                 */
    .word  SPDIF_RX_IRQHandler             /* 94 SPDIF-RX                 */
    .word  FMPI2C1_EV_IRQHandler           /* 95 FMPI2C1 event            */
    .word  FMPI2C1_ER_IRQHandler           /* 96 FMPI2C1 error            */


/*
 * =============================================================================
 *  Weak IRQ aliases — every named handler defaults to Default_Handler
 *  and can be overridden by providing a strong symbol with the same name.
 * =============================================================================
 */
.weak  NMI_Handler
.thumb_set NMI_Handler, Default_Handler
.weak  HardFault_Handler
.thumb_set HardFault_Handler, Default_Handler
.weak  MemManage_Handler
.thumb_set MemManage_Handler, Default_Handler
.weak  BusFault_Handler
.thumb_set BusFault_Handler, Default_Handler
.weak  UsageFault_Handler
.thumb_set UsageFault_Handler, Default_Handler
.weak  SVC_Handler
.thumb_set SVC_Handler, Default_Handler
.weak  DebugMon_Handler
.thumb_set DebugMon_Handler, Default_Handler
.weak  PendSV_Handler
.thumb_set PendSV_Handler, Default_Handler
.weak  SysTick_Handler
.thumb_set SysTick_Handler, Default_Handler

.weak  WWDG_IRQHandler
.thumb_set WWDG_IRQHandler, Default_Handler
.weak  PVD_IRQHandler
.thumb_set PVD_IRQHandler, Default_Handler
.weak  TAMP_STAMP_IRQHandler
.thumb_set TAMP_STAMP_IRQHandler, Default_Handler
.weak  RTC_WKUP_IRQHandler
.thumb_set RTC_WKUP_IRQHandler, Default_Handler
.weak  FLASH_IRQHandler
.thumb_set FLASH_IRQHandler, Default_Handler
.weak  RCC_IRQHandler
.thumb_set RCC_IRQHandler, Default_Handler
.weak  EXTI0_IRQHandler
.thumb_set EXTI0_IRQHandler, Default_Handler
.weak  EXTI1_IRQHandler
.thumb_set EXTI1_IRQHandler, Default_Handler
.weak  EXTI2_IRQHandler
.thumb_set EXTI2_IRQHandler, Default_Handler
.weak  EXTI3_IRQHandler
.thumb_set EXTI3_IRQHandler, Default_Handler
.weak  EXTI4_IRQHandler
.thumb_set EXTI4_IRQHandler, Default_Handler
.weak  DMA1_Stream0_IRQHandler
.thumb_set DMA1_Stream0_IRQHandler, Default_Handler
.weak  DMA1_Stream1_IRQHandler
.thumb_set DMA1_Stream1_IRQHandler, Default_Handler
.weak  DMA1_Stream2_IRQHandler
.thumb_set DMA1_Stream2_IRQHandler, Default_Handler
.weak  DMA1_Stream3_IRQHandler
.thumb_set DMA1_Stream3_IRQHandler, Default_Handler
.weak  DMA1_Stream4_IRQHandler
.thumb_set DMA1_Stream4_IRQHandler, Default_Handler
.weak  DMA1_Stream5_IRQHandler
.thumb_set DMA1_Stream5_IRQHandler, Default_Handler
.weak  DMA1_Stream6_IRQHandler
.thumb_set DMA1_Stream6_IRQHandler, Default_Handler
.weak  ADC_IRQHandler
.thumb_set ADC_IRQHandler, Default_Handler
.weak  CAN1_TX_IRQHandler
.thumb_set CAN1_TX_IRQHandler, Default_Handler
.weak  CAN1_RX0_IRQHandler
.thumb_set CAN1_RX0_IRQHandler, Default_Handler
.weak  CAN1_RX1_IRQHandler
.thumb_set CAN1_RX1_IRQHandler, Default_Handler
.weak  CAN1_SCE_IRQHandler
.thumb_set CAN1_SCE_IRQHandler, Default_Handler
.weak  EXTI9_5_IRQHandler
.thumb_set EXTI9_5_IRQHandler, Default_Handler
.weak  TIM1_BRK_TIM9_IRQHandler
.thumb_set TIM1_BRK_TIM9_IRQHandler, Default_Handler
.weak  TIM1_UP_TIM10_IRQHandler
.thumb_set TIM1_UP_TIM10_IRQHandler, Default_Handler
.weak  TIM1_TRG_COM_TIM11_IRQHandler
.thumb_set TIM1_TRG_COM_TIM11_IRQHandler, Default_Handler
.weak  TIM1_CC_IRQHandler
.thumb_set TIM1_CC_IRQHandler, Default_Handler
.weak  TIM2_IRQHandler
.thumb_set TIM2_IRQHandler, Default_Handler
.weak  TIM3_IRQHandler
.thumb_set TIM3_IRQHandler, Default_Handler
.weak  TIM4_IRQHandler
.thumb_set TIM4_IRQHandler, Default_Handler
.weak  I2C1_EV_IRQHandler
.thumb_set I2C1_EV_IRQHandler, Default_Handler
.weak  I2C1_ER_IRQHandler
.thumb_set I2C1_ER_IRQHandler, Default_Handler
.weak  I2C2_EV_IRQHandler
.thumb_set I2C2_EV_IRQHandler, Default_Handler
.weak  I2C2_ER_IRQHandler
.thumb_set I2C2_ER_IRQHandler, Default_Handler
.weak  SPI1_IRQHandler
.thumb_set SPI1_IRQHandler, Default_Handler
.weak  SPI2_IRQHandler
.thumb_set SPI2_IRQHandler, Default_Handler
.weak  USART1_IRQHandler
.thumb_set USART1_IRQHandler, Default_Handler
.weak  USART2_IRQHandler
.thumb_set USART2_IRQHandler, Default_Handler
.weak  USART3_IRQHandler
.thumb_set USART3_IRQHandler, Default_Handler
.weak  EXTI15_10_IRQHandler
.thumb_set EXTI15_10_IRQHandler, Default_Handler
.weak  RTC_Alarm_IRQHandler
.thumb_set RTC_Alarm_IRQHandler, Default_Handler
.weak  OTG_FS_WKUP_IRQHandler
.thumb_set OTG_FS_WKUP_IRQHandler, Default_Handler
.weak  TIM8_BRK_TIM12_IRQHandler
.thumb_set TIM8_BRK_TIM12_IRQHandler, Default_Handler
.weak  TIM8_UP_TIM13_IRQHandler
.thumb_set TIM8_UP_TIM13_IRQHandler, Default_Handler
.weak  TIM8_TRG_COM_TIM14_IRQHandler
.thumb_set TIM8_TRG_COM_TIM14_IRQHandler, Default_Handler
.weak  TIM8_CC_IRQHandler
.thumb_set TIM8_CC_IRQHandler, Default_Handler
.weak  DMA1_Stream7_IRQHandler
.thumb_set DMA1_Stream7_IRQHandler, Default_Handler
.weak  FMC_IRQHandler
.thumb_set FMC_IRQHandler, Default_Handler
.weak  SDIO_IRQHandler
.thumb_set SDIO_IRQHandler, Default_Handler
.weak  TIM5_IRQHandler
.thumb_set TIM5_IRQHandler, Default_Handler
.weak  SPI3_IRQHandler
.thumb_set SPI3_IRQHandler, Default_Handler
.weak  UART4_IRQHandler
.thumb_set UART4_IRQHandler, Default_Handler
.weak  UART5_IRQHandler
.thumb_set UART5_IRQHandler, Default_Handler
.weak  TIM6_DAC_IRQHandler
.thumb_set TIM6_DAC_IRQHandler, Default_Handler
.weak  TIM7_IRQHandler
.thumb_set TIM7_IRQHandler, Default_Handler
.weak  DMA2_Stream0_IRQHandler
.thumb_set DMA2_Stream0_IRQHandler, Default_Handler
.weak  DMA2_Stream1_IRQHandler
.thumb_set DMA2_Stream1_IRQHandler, Default_Handler
.weak  DMA2_Stream2_IRQHandler
.thumb_set DMA2_Stream2_IRQHandler, Default_Handler
.weak  DMA2_Stream3_IRQHandler
.thumb_set DMA2_Stream3_IRQHandler, Default_Handler
.weak  DMA2_Stream4_IRQHandler
.thumb_set DMA2_Stream4_IRQHandler, Default_Handler
.weak  CAN2_TX_IRQHandler
.thumb_set CAN2_TX_IRQHandler, Default_Handler
.weak  CAN2_RX0_IRQHandler
.thumb_set CAN2_RX0_IRQHandler, Default_Handler
.weak  CAN2_RX1_IRQHandler
.thumb_set CAN2_RX1_IRQHandler, Default_Handler
.weak  CAN2_SCE_IRQHandler
.thumb_set CAN2_SCE_IRQHandler, Default_Handler
.weak  OTG_FS_IRQHandler
.thumb_set OTG_FS_IRQHandler, Default_Handler
.weak  DMA2_Stream5_IRQHandler
.thumb_set DMA2_Stream5_IRQHandler, Default_Handler
.weak  DMA2_Stream6_IRQHandler
.thumb_set DMA2_Stream6_IRQHandler, Default_Handler
.weak  DMA2_Stream7_IRQHandler
.thumb_set DMA2_Stream7_IRQHandler, Default_Handler
.weak  USART6_IRQHandler
.thumb_set USART6_IRQHandler, Default_Handler
.weak  I2C3_EV_IRQHandler
.thumb_set I2C3_EV_IRQHandler, Default_Handler
.weak  I2C3_ER_IRQHandler
.thumb_set I2C3_ER_IRQHandler, Default_Handler
.weak  OTG_HS_EP1_OUT_IRQHandler
.thumb_set OTG_HS_EP1_OUT_IRQHandler, Default_Handler
.weak  OTG_HS_EP1_IN_IRQHandler
.thumb_set OTG_HS_EP1_IN_IRQHandler, Default_Handler
.weak  OTG_HS_WKUP_IRQHandler
.thumb_set OTG_HS_WKUP_IRQHandler, Default_Handler
.weak  OTG_HS_IRQHandler
.thumb_set OTG_HS_IRQHandler, Default_Handler
.weak  DCMI_IRQHandler
.thumb_set DCMI_IRQHandler, Default_Handler
.weak  FPU_IRQHandler
.thumb_set FPU_IRQHandler, Default_Handler
.weak  SPI4_IRQHandler
.thumb_set SPI4_IRQHandler, Default_Handler
.weak  SAI1_IRQHandler
.thumb_set SAI1_IRQHandler, Default_Handler
.weak  SAI2_IRQHandler
.thumb_set SAI2_IRQHandler, Default_Handler
.weak  QUADSPI_IRQHandler
.thumb_set QUADSPI_IRQHandler, Default_Handler
.weak  CEC_IRQHandler
.thumb_set CEC_IRQHandler, Default_Handler
.weak  SPDIF_RX_IRQHandler
.thumb_set SPDIF_RX_IRQHandler, Default_Handler
.weak  FMPI2C1_EV_IRQHandler
.thumb_set FMPI2C1_EV_IRQHandler, Default_Handler
.weak  FMPI2C1_ER_IRQHandler
.thumb_set FMPI2C1_ER_IRQHandler, Default_Handler
