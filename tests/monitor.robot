
*** Settings ***
Documentation     Monitoramento continuo de pesquisas no Google.
Library           Browser
Library           Collections
Variables         ../config/urls.py


*** Keywords ***
Detectar CAPTCHA
    ${captcha_iframe}=    Run Keyword And Return Status
    ...    Wait For Elements State
    ...    css=iframe[src*="recaptcha"]
    ...    attached
    ...    timeout=1s

    ${captcha_form}=    Run Keyword And Return Status
    ...    Wait For Elements State
    ...    css=#captcha-form
    ...    visible
    ...    timeout=1s

    IF    ${captcha_iframe} or ${captcha_form}
        RETURN    ${TRUE}
    END

    RETURN    ${FALSE}


Pesquisar No Google
    [Arguments]    ${query}

    Log To Console    \n[PESQUISA] ${query}

    Go To    https://www.google.com/

    ${blocked}=    Detectar CAPTCHA
    IF    ${blocked}
        Log To Console    [ALERTA] CAPTCHA detectado. Pulando o restante deste ciclo.
        RETURN    BLOCKED_CAPTCHA
    END

    Wait For Elements State
    ...    css=textarea[name="q"]
    ...    visible
    ...    timeout=${ELEMENT_TIMEOUT}

    Fill Text    css=textarea[name="q"]    ${query}
    Press Keys    css=textarea[name="q"]    Enter

    ${blocked}=    Detectar CAPTCHA
    IF    ${blocked}
        Log To Console    [ALERTA] CAPTCHA detectado nos resultados.
        RETURN    BLOCKED_CAPTCHA
    END

    Wait For Elements State
    ...    css=#search
    ...    visible
    ...    timeout=${ELEMENT_TIMEOUT}

    Log To Console    [OK] Resultados carregados para: ${query}

    Sleep    ${SEARCH_DELAY_SECONDS}s

    RETURN    OK


*** Test Cases ***
Monitorar Pesquisas Continuamente
    Log To Console    Iniciando monitoramento de pesquisas.
    Log To Console    Pressione Ctrl+C para interromper.

    WHILE    True
        Log To Console    \n========== INICIO DO CICLO ==========

        TRY
            New Browser    chromium    headless=${HEADLESS}
            New Context
            New Page

            FOR    ${query}    IN    @{SEARCH_QUERIES}
                ${status}    ${result}=    Run Keyword And Ignore Error
                ...    Pesquisar No Google    ${query}

                IF    $status == 'FAIL'
                    Log To Console    [FALHA] ${query}: ${result}
                    Log    FALHA | ${query} | ${result}

                ELSE IF    $result == 'BLOCKED_CAPTCHA'
                    Log To Console    [ALERTA] Interrompendo este ciclo.
                    BREAK
                END
            END

        FINALLY
            Log To Console    Encerrando navegador do ciclo.
            Run Keyword And Ignore Error    Close Browser
        END

        Log To Console    ========== FIM DO CICLO ==========

        IF    ${CYCLE_DELAY_SECONDS} > 0
            Sleep    ${CYCLE_DELAY_SECONDS}s
        END
    END
