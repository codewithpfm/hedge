type NormalizeData = (data: unknown) => any;

export const normalizeData: NormalizeData = (data: unknown)  => {

    if(data instanceof Array){
        return data.map(normalizeData);
    }

    if(data instanceof Date){
        return data;
    }


    if(data instanceof Object){
        const normalized = {};
        for(const key in data){
            normalized[key as keyof typeof data] = normalizeData(data[key as keyof typeof data]);
        }
        return normalized;
    }

    if(typeof data === "string"){
        return data.trim();
    }

    if(typeof data === "bigint"){
        return Number(data);
    }

    return data;
};