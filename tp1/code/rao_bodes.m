% Script de Análisis de Función de Transferencia Universal
clear; clc; close all;
try
    pkg load control;
catch
    warning('Paquete "control" no cargado. Puede fallar en Octave.');
end

% Intentar cargar bodas si no está en el path de búsqueda de Octave
if exist('bodas', 'file') == 0
    try
        addpath(tilde_expand('~/.octave_libs/bodas'));
    catch
        % Fallback al path absoluto por si falla tilde_expand
        addpath('/home/valen/.octave_libs/bodas');
    end
end

fprintf('=== Análisis de H(s) Asintótico (Repo: bodas) ===\n\n');
fprintf('Ingrese los polinomios de la Función H(s).\n');
fprintf('Ejemplo: para s^2 + 200s + 6400, ingrese [1 200 6400]\n\n');

num = input('Ingrese el vector del NUMERADOR: ');
den = input('Ingrese el vector del DENOMINADOR: ');
H = tf(num, den);

fprintf('\n--- FUNCIÓN DE TRANSFERENCIA H(s) INGRESADA: ---\n');
display(H);

fprintf('Ejecutando bodas.m para el Diagrama Asintótico...\n');
try
    [G_out, w] = bodas(H);
    fprintf('¡Diagramas de Bode generados!\n');
catch err
    fprintf('\n[ERROR] No se pudo ejecutar bodas().\n');
    fprintf('Verifique que "bodas.m" esté en esta carpeta o agregada al PATH de Octave.\n');
    fprintf('Mensaje: %s\n', err.message);
end

fprintf('\nGenerando Diagrama Polar...\n');
figure('Name', 'Diagrama Polar de H(s)'); 
nyquist(H); grid on; title('Diagrama Polar (Locus de H(jw))');

fprintf('\nAnálisis finalizado. Revise las figuras.\n');
