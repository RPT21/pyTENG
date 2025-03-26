import pandas as pd

def read_excel(file_path):

    # Llegim l'excel
    dataframe = pd.read_excel(file_path)

    # Obtenim els noms de les columnes
    header = dataframe.columns

    # Obtenim el nombre de files i columnes (excloent el header)
    rows, columns = dataframe.shape

    # Diccionari de parametres
    parameterDict = dict()

    # Omplim el diccionari
    for i in range(columns):
        parameterDict[header[i]] = dataframe[header[i]].tolist()

    return parameterDict

if __name__ == "__main__":
    file_path = 'C:/Users/rpieres/PycharmProjects/pyTENG/ParameterFormat.xlsx'
    print(read_excel(file_path))

