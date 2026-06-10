% -------------------------------------------------------------------
% Cátedra: Teoría de Circuitos II - UTN FRC
% Script de Análisis de Función de Transferencia Universal
% Utiliza la librería "bodas" para trazar asíntotas exactas.
% -------------------------------------------------------------------

clear; clc; close all;

% Intentamos cargar el paquete de control, necesario para la función tf()
try
    pkg load control;
catch
    warning('El paquete "control" no está instalado o cargado. Puede fallar si no se usa MATLAB.');
end

fprintf('=======================================================\n');
fprintf('  Análisis de H(s) con Trazado Asintótico (Repo: bodas)\n');
fprintf('=======================================================\n\n');

fprintf('Ingrese los polinomios de la Función de Transferencia H(s).\n');
fprintf('Use el formato de vector de coeficientes descendentes en "s".\n');
fprintf('Ejemplo: para s^2 + 200s + 6400, ingrese [1 200 6400]\n\n');

% 1. Ingreso de datos por parte del usuario
num = input('Ingrese el vector del NUMERADOR: ');
den = input('Ingrese el vector del DENOMINADOR: ');

% 2. Creación del sistema
H = tf(num, den);

fprintf('\n-------------------------------------------------------\n');
fprintf('FUNCIÓN DE TRANSFERENCIA H(s) INGRESADA:\n');
display(H);
fprintf('-------------------------------------------------------\n\n');

% 3. Generación del Diagrama de Bode con bodas.m
fprintf('Ejecutando bodas.m para generar el Diagrama Asintótico...\n');
try
    % La función bodas(G) tomará el objeto tf y generará las gráficas
    % comparando el Bode real con la aproximación asintótica.
    [G_out, w] = bodas(H);
    fprintf('¡Diagramas de Bode generados con éxito!\n');
catch err
    fprintf('\n[ERROR] No se pudo ejecutar la función bodas().\n');
    fprintf('-> Por favor, verifique que los archivos "bodas.m" y "tight_subplot.m"\n');
    fprintf('   estén descargados en la misma carpeta donde está ejecutando este script.\n');
    fprintf('Mensaje del sistema: %s\n', err.message);
end

% 4. Generación del Diagrama Polar (Nyquist)
fprintf('\nGenerando Diagrama Polar...\n');
% Abrimos una nueva figura para que bodas.m no la sobreescriba
figure('Name', 'Diagrama Polar de H(s)'); 
nyquist(H);
grid on;
title('Diagrama Polar (Locus de H(jw))');

fprintf('\nAnálisis finalizado. Revise las ventanas de figuras emergentes.\n');
fprintf('=======================================================\n');
